import inotify

#outputs = inotify.wait('-m -r /tmp')
#outputs = inotify.wait('-m -v -r /tmp')
outputs = inotify.wait('-m -v -r -t 10 /tmp')
#print(outputs)
for output in outputs:
    print(output)

#outputs = inotify.wait('-r -v /tmp')
#print(outputs)

#outputs = inotify.wait("-r -v --format '%w %e' /tmp")
#print(outputs)
