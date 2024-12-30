#!/usr/bin/env python3

from ctypes import CDLL, CFUNCTYPE, c_char_p, c_int, c_uint32
from ctypes.util import find_library
import argparse
import multiprocessing
import os
import pathlib
import signal
import struct
import sys
import time

def _print_verbose(*args):
    pass

__libc = CDLL(find_library("c"))

inotify_init = CFUNCTYPE(c_int)(("inotify_init", __libc), ())
inotify_init1 = CFUNCTYPE(c_int, c_int)(("inotify_init", __libc), ((1, "flags"),))

inotify_add_watch = CFUNCTYPE(c_int, c_int, c_char_p, c_uint32)(
                        ("inotify_add_watch", __libc), ((1, "fd"), (1, "pathname"), (1, "mask")))

inotify_rm_watch = CFUNCTYPE(c_int, c_int, c_int)(
                       ("inotify_rm_watch", __libc), ((1, "fd"), (1, "wd")))

_EVENTS = {
    "ACCESS"           : 0x00000001,
    "MODIFY"           : 0x00000002,
    "ATTRIB"           : 0x00000004,
    "CLOSE_WRITE"      : 0x00000008,
    "CLOSE_NOWRITE"    : 0x00000010,
    "OPEN"             : 0x00000020,
    "MOVED_FROM"       : 0x00000040,
    "MOVED_TO"         : 0x00000080,
    "CREATE"           : 0x00000100,
    "DELETE"           : 0x00000200,
    "DELETE_SELF"      : 0x00000400,
    "MOVE_SELF"        : 0x00000800,
    
    "UNMOUNT"          : 0x00002000,
    "Q_OVERFLOW"       : 0x00004000,
    "IGNORED"          : 0x00008000,
    
    "CLOSE"            : 0x00000008 | 0x00000010, #CLOSE_WRITE | CLOSE_NOWRITE
    "MOVE"             : 0x00000040 | 0x00000080, #MOVED_FROM | MOVED_TO
    
    "ONLYDIR"          : 0x01000000,
    "DONT_FOLLOW"      : 0x02000000,
    "EXCL_UNLINK"      : 0x04000000,
    "MASK_ADD"         : 0x20000000,
    "ISDIR"            : 0x40000000,
    "ONESHOT"          : 0x80000000
}

_watch_descriptors = {}

def _decode_flag(flag):
    flag_names = _EVENTS.copy()
    del flag_names["MOVE"]
    r = []
    for n in flag_names.keys():
        if _EVENTS[n] & flag != 0:
            r.append(n)
    return r

def _handler(signum, frame):
    sys.exit(2)

def _kill_timer(timeout, pid):
    _print_verbose(f"wait for {timeout} seconds")
    time.sleep(timeout)
    _print_verbose("kill main process")
    os.kill(pid, signal.SIGQUIT)
    #sys.exit(2)

_process = None
def _reset(timeout, pid):
    global _process
    if _process:
        _print_verbose("kill process")
        _process.kill()
    _process = multiprocessing.Process(target=_kill_timer, args=(timeout, pid))
    _print_verbose("start process")
    _process.start()

_pid = os.getpid()
def _detect_inotify(fd, timeout):
    global _pid
    if timeout > 0:
        _reset(timeout, _pid)
    buf = os.read(fd, 4096)
    i = 0
    fmt = 'iIII'
    fmt_size = struct.calcsize(fmt)
    while i < len(buf):
        wd, mask, cookie, name_len = struct.unpack_from(fmt, buf, i)
        i += fmt_size
        name = buf[i:i+name_len]
        i += name_len
        _print_verbose("wd: {} mask: {:08x} path: {}".format(wd, mask, name.decode()))
        yield [wd, mask, name.decode()]

_status_code = 0
def wait(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', metavar='path', nargs='+', help='directory or file to watch')
    parser.add_argument('-e', '--event', action='append', default=[], type=str,
        #choices=[x for x in _EVENTS.keys()],
        metavar='<event>', help='event name to watch')
    parser.add_argument('-m', '--monitor', action='store_true', default=False, help='monitor mode')
    parser.add_argument('-r', '--recursive', action='store_true', default=False, help='detect under the directory')
    def check_nonnegative(value):
        number = float(value)
        if number < 0:
            raise argparse.ArgumentTypeError("%s is an invalid negative value" % number)
        return number
    parser.add_argument('-t', '--timeout', action='store', type=check_nonnegative, default=0, metavar='<seconds>',
        help='waiting for specified time if non event occurred within <timeout>')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose print')
    #parser.add_argument('--format', action='store_const', const='%%w %%e', metavar='<fmt>',
    parser.add_argument('--format', required=False, metavar='<fmt>',
        help="""Output in a user-specified format, using printf-like syntax.  The event strings output are  limited  to
              around 4000 characters and will be truncated to this length.  The following conversions are supported:

       %%w     This will be replaced with the name of the Watched file on which an event occurred.

       %%f     When  an  event occurs within a directory, this will be replaced with the name of the File which caused
              the event to occur.  Otherwise, this will be replaced with an empty string.

       %%e     Replaced with the Event(s) which occurred, comma-separated.

       %%Xe    Replaced with the Event(s) which occurred, separated by whichever character is in the place of `X'.

       %%T     Replaced with the current Time in the format specified by the --timefmt option, which should be a  for‐
              mat string suitable for passing to strftime(3).""")
    parser.add_argument('--timefmt', required=False, metavar='<fmt>',
        help="Set a time format string as accepted by strftime(3) for use with the `%%T' conversion in the --format option.")

    args = parser.parse_args(argv)

    events_inputs  = args.event
    monitor_mode   = args.monitor
    target_paths   = args.paths
    recursive_mode = args.recursive
    timeout        = args.timeout
    verbose_mode   = args.verbose

    # verbose setting if verbose mode
    global _print_verbose
    if verbose_mode:
        _print_verbose = print

    _print_verbose(argv)

    # set status code at timeout
    signal.signal(signal.SIGQUIT, _handler)

    # reveal watch descriptor
    def reveal_watch_descriptors(signum, frame):
        print(_watch_descriptors)
    signal.signal(signal.SIGUSR1, reveal_watch_descriptors)

    # parse event option input
    events = []
    for events_input in events_inputs:
        for event_string in events_input.split(","):
            e = event_string.upper()
            if e not in _EVENTS:
                parser.print_help()
                _status_code = 1
                #sys.exit(1)
            events.append(e)
    _print_verbose(f"specified events: {events}")

    # initialize event mask
    mask = 0
    for x in events:
        mask |= _EVENTS[x]
    if mask == 0:
        mask = 0xfff

    print('watching {} for inotify events: {}'.format(
        args.paths, ",".join(_decode_flag(mask))), file=sys.stderr, flush=True)

    try:
        fd = inotify_init()
        paths = []
        for path in target_paths:
            if not pathlib.Path(path).exists():
                raise FileNotFoundError(f"specified file is not exist: {path}")
            if pathlib.Path(path).is_dir():
                paths.append(path.rstrip(os.sep) + os.sep)
                if recursive_mode:
                    # walk directory tree when recusive mode
                    for root, dirs, _ in os.walk(path):
                        for d in dirs:
                            paths.append(root + os.path.sep + d.rstrip(os.sep) + os.sep)
            else:
                paths.append(path)
        # assign watch descriptor to each target directory
        for path in paths:
            wd = inotify_add_watch(fd, path.encode(), mask)
            _print_verbose("inotify_add_watch {} {} {} => {}".format(fd, path, ",".join(_decode_flag(mask)), wd))
            _watch_descriptors[wd] = path
        if monitor_mode:
            deleting_watch_descriptor = None
            while True:
                gen_detected = _detect_inotify(fd, timeout)
                for detected in gen_detected:
                    #del name
                    [wd, flags, name] = detected
                    #[wd, flags, name] = detected if len(detected) == 3 else [detected[0], detected[1], ""]
                    directory = _watch_descriptors[wd]
                    # print if this program is called directly. yield python values if this program is called as module.
                    print("{} {} {}".format(directory, ",".join(_decode_flag(flags)), name.replace('\0', '')), flush=True)
                    if recursive_mode:
                        # if directory is created, add it to watch
                        if (flags & _EVENTS['CREATE'] != 0) and (flags & _EVENTS['ISDIR'] != 0):
                            #path = directory + name.rstrip(os.sep).replace('\0', '') + os.sep
                            path = directory + name.replace('\0', '') + os.sep
                            # TODO confirming
                            wd = inotify_add_watch(fd, path.encode(), mask)
                            #wd = inotify_add_watch(fd, path.encode(), mask)
                            _print_verbose("inotify_add_watch {} {} {} => {}".format(fd, path, ",".join(_decode_flag(mask)), wd))
                            _watch_descriptors[wd] = path
                        # if directory is deleted, remove it from watch
                        #elif (flags & _EVENTS['DELETE'] != 0) and (flags & _EVENTS['ISDIR'] != 0):
                        elif (flags & _EVENTS['DELETE_SELF'] != 0):
                            _print_verbose("deleting watch descriptor {}".format(wd))
                            deleting_watch_descriptor = wd
                        elif (flags & _EVENTS['IGNORED'] != 0):
                            if not deleting_watch_descriptor:
                                continue
                            _print_verbose("inotify_rm_watch {} {}".format(fd, wd))
                            inotify_rm_watch(fd, wd)
                            del _watch_descriptors[wd]
                            deleting_watch_descriptor = None
        else:
            [wd, flags, name] = next(_detect_inotify(fd, timeout))
            directory = _watch_descriptors[wd]
            # print if this program is called directly. yield python values if this program is called as module.
            print("{} {} {}".format(directory, ",".join(_decode_flag(flags)), name.replace('\0', '')), flush=True)
        _status_code = 0
    except FileNotFoundError as e:
        _print_verbose(e)
        _status_code = 1
    except KeyboardInterrupt:
        _print_verbose("KeyboardInterrupt")
        _status_code = 130
    finally:
        global _process
        if _process:
            _process.kill()
        for wd in _watch_descriptors.keys():
            inotify_rm_watch(fd, wd)
        os.close(fd)
    return _status_code

if __name__ == '__main__':
    sys.exit(wait(sys.argv[1:]))
