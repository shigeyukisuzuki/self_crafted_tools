import os
import pytest
import shutil
import subprocess
import tempfile
import time

command = ["python3", "inotify.py"]
#command = ["inotifywait"]

def test_inotifywait_file_creation():
    """
    Test that inotifywait detects file creation events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_file = os.path.join(watched_dir, "testfile.txt")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "create", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Create a file in the watched directory
            with open(test_file, "w") as f:
                f.write("This is a test file.")

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()
            
            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ CREATE testfile.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_timeout():
    """
    Test that inotifywait respects the --timeout option.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir

        # Start inotifywait with a timeout of 2 seconds
        cmd = [*command, "--timeout", "2", "-e", "create", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Wait for timeout
            time.sleep(3)

            # Wait for the process to finish
            stdout, stderr = process.communicate()

            # Verify that inotifywait timed out without events when the return code is assumed as 2
            return_code = process.returncode
            assert return_code == 2

        finally:
            # Ensure the process is terminated
            if process.poll() is None:
                process.terminate()
                process.wait()

def test_inotifywait_file_modification():
    """
    Test that inotifywait detects file modification events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_file = os.path.join(watched_dir, "testfile.txt")

        # Create a file to be modified
        with open(test_file, "w") as f:
            f.write("Initial content.")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "modify", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Modify the file
            with open(test_file, "a") as f:
                f.write("Additional content.")

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ MODIFY testfile.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_file_deletion():
    """
    Test that inotifywait detects file deletion events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_file = os.path.join(watched_dir, "testfile.txt")

        # Create a file to be deleted
        with open(test_file, "w") as f:
            f.write("This file will be deleted.")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "delete", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Delete the file
            os.remove(test_file)

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ DELETE testfile.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_directory_creation():
    """
    Test that inotifywait detects directory creation events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_subdir = os.path.join(watched_dir, "subdir")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "create", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Create a subdirectory
            os.mkdir(test_subdir)

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ CREATE,ISDIR subdir"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_file_move():
    """
    Test that inotifywait detects file move events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        source_file = os.path.join(watched_dir, "source.txt")
        dest_file = os.path.join(watched_dir, "dest.txt")

        # Create a file to be moved
        with open(source_file, "w") as f:
            f.write("This file will be moved.")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "move", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Move the file
            os.rename(source_file, dest_file)

            # Wait for inotifywait output
            stdout_output = { process.stdout.readline().strip(), 
                            process.stdout.readline().strip() }

            # Check if inotifywait output matches the expected event
            expected_output = { f"{watched_dir}/ MOVED_TO dest.txt", 
                                f"{watched_dir}/ MOVED_FROM source.txt" }
            assert expected_output == stdout_output

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_recursive():
    """
    Test that inotifywait detects events recursively in subdirectories.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        subdir = os.path.join(watched_dir, "subdir")
        os.mkdir(subdir)
        test_file = os.path.join(subdir, "testfile.txt")

        # Start inotifywait as a subprocess to monitor the directory recursively
        cmd = [*command, "-m", "-r", "-e", "create", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Create a file in the subdirectory
            with open(test_file, "w") as f:
                f.write("This is a test file.")

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{subdir}/ CREATE testfile.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_symlink_deletion():
    """
    Test that inotifywait detects symlink deletion events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        target_file = os.path.join(watched_dir, "target.txt")
        symlink = os.path.join(watched_dir, "symlink.txt")

        # Create a target file and symlink
        with open(target_file, "w") as f:
            f.write("This is a target file.")
        os.symlink(target_file, symlink)

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "delete", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Delete the symlink
            os.remove(symlink)

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ DELETE symlink.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_directory_deletion():
    """
    Test that inotifywait detects directory deletion events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_subdir = os.path.join(watched_dir, "subdir")

        # Create a subdirectory
        os.mkdir(test_subdir)

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "delete", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Delete the subdirectory
            os.rmdir(test_subdir)

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ DELETE,ISDIR subdir"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_multiple_events():
    """
    Test that inotifywait detects multiple events in sequence.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_file = os.path.join(watched_dir, "testfile.txt")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "create,modify", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Create a file
            with open(test_file, "w") as f:
                f.write("Initial content.")

            # Wait for the create event
            stdout_line_create = process.stdout.readline().strip()
            expected_output_create = f"{watched_dir}/ CREATE testfile.txt"
            assert expected_output_create in stdout_line_create

            # Modify the file
            with open(test_file, "a") as f:
                f.write(" Additional content.")

            # Wait for the modify event
            stdout_line_modify = process.stdout.readline().strip()
            expected_output_modify = f"{watched_dir}/ MODIFY testfile.txt"
            assert expected_output_modify in stdout_line_modify

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_file_access():
    """
    Test that inotifywait detects file access events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        test_file = os.path.join(watched_dir, "testfile.txt")

        # Create a file to be accessed
        with open(test_file, "w") as f:
            f.write("This file will be accessed.")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "access", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Access the file
            with open(test_file, "r") as f:
                _ = f.read()

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ ACCESS testfile.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_file_rename():
    """
    Test that inotifywait detects file rename events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        original_file = os.path.join(watched_dir, "original.txt")
        renamed_file = os.path.join(watched_dir, "renamed.txt")

        # Create a file
        with open(original_file, "w") as f:
            f.write("This file will be renamed.")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "move", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Rename the file
            os.rename(original_file, renamed_file)

            # Wait for inotifywait output
            stdout_output = { process.stdout.readline().strip(), 
                            process.stdout.readline().strip() }

            # Check if inotifywait output matches the expected event
            expected_output = { f"{watched_dir}/ MOVED_TO renamed.txt",
                                f"{watched_dir}/ MOVED_FROM original.txt" }
            assert expected_output == stdout_output

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_directory_rename():
    """
    Test that inotifywait detects directory rename events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        original_dir = os.path.join(watched_dir, "original_dir")
        renamed_dir = os.path.join(watched_dir, "renamed_dir")

        # Create a directory
        os.mkdir(original_dir)

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "move", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Rename the directory
            os.rename(original_dir, renamed_dir)

            # Wait for inotifywait output
            stdout_output = { process.stdout.readline().strip(),
                            process.stdout.readline().strip() }

            # Check if inotifywait output matches the expected event
            expected_output = { f"{watched_dir}/ MOVED_TO,ISDIR renamed_dir",
                                f"{watched_dir}/ MOVED_FROM,ISDIR original_dir" }
            assert expected_output == stdout_output

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_file_copy():
    """
    Test that inotifywait detects file copy events.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = tempdir
        original_file = os.path.join(watched_dir, "original.txt")
        copied_file = os.path.join(watched_dir, "copied.txt")

        # Create a file
        with open(original_file, "w") as f:
            f.write("This file will be copied.")

        # Start inotifywait as a subprocess to monitor the directory
        cmd = [*command, "-m", "-e", "create", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Give inotifywait some time to start
            time.sleep(1)

            # Copy the file
            shutil.copy2(original_file, copied_file)

            # Wait for inotifywait output
            stdout_line = process.stdout.readline().strip()

            # Check if inotifywait output matches the expected event
            expected_output = f"{watched_dir}/ CREATE copied.txt"
            assert expected_output in stdout_line

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

def test_inotifywait_no_event_outside_watched_dir():
    """
    Test that inotifywait does not detect events outside the watched directory.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        watched_dir = os.path.join(tempdir, "watched")
        outside_dir = os.path.join(tempdir, "outside")
        test_file = os.path.join(outside_dir, "testfile.txt")

        # Create directories
        os.mkdir(watched_dir)
        os.mkdir(outside_dir)

        # Start inotifywait as a subprocess to monitor the watched directory
        cmd = [*command, "-m", "-e", "create", watched_dir]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            stdout = None
            try:
                # consume message to standard output
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                pass

            # Create a file outside the watched directory
            with open(test_file, "w") as f:
                f.write("This is outside the watched directory.")

            try:
                # Ensure no output is generated for the outside event
                #time.sleep(1)  # Wait to ensure no event is detected
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                assert stdout == None

        finally:
            # Terminate the inotifywait process
            process.terminate()
            process.wait()

if __name__ == "__main__":
    pytest.main(["-v", __file__])

