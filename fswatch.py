#!/usr/bin/env python
"""
fswatch.py
Marcus Kazmierczak, marcus@mkaz.com
http://github.com/mkaz/fswatch/

This script will watch a local directory using Mac OS X FSEvents
and on change will sync to a remote directory. The script can be
easily modified to do whatever you want on a change event.

requires: pip install MacFSEvents

Note: if you are running against a large directory, it will
take awhile at the beginning, my hunch is it needs to traverse
all sub-directories and attach the listeners everywhere

tested on OS X 10.9.3
"""

"""
Reference of FSEventStreamEventFlags,
https://developer.apple.com/library/mac/documentation/Darwin/Reference/FSEvents_Ref/Reference/reference.html

enum {
   kFSEventStreamEventFlagNone = 0x00000000,
   kFSEventStreamEventFlagMustScanSubDirs = 0x00000001,
   kFSEventStreamEventFlagUserDropped = 0x00000002,
   kFSEventStreamEventFlagKernelDropped = 0x00000004,
   kFSEventStreamEventFlagEventIdsWrapped = 0x00000008,
   kFSEventStreamEventFlagHistoryDone = 0x00000010,
   kFSEventStreamEventFlagRootChanged = 0x00000020,
   kFSEventStreamEventFlagMount = 0x00000040,
   kFSEventStreamEventFlagUnmount = 0x00000080, /* These flags are only set if you specified the FileEvents*/
   /* flags when creating the stream.*/
   kFSEventStreamEventFlagItemCreated = 0x00000100,
   kFSEventStreamEventFlagItemRemoved = 0x00000200,
   kFSEventStreamEventFlagItemInodeMetaMod = 0x00000400,
   kFSEventStreamEventFlagItemRenamed = 0x00000800,
   kFSEventStreamEventFlagItemModified = 0x00001000,
   kFSEventStreamEventFlagItemFinderInfoMod = 0x00002000,
   kFSEventStreamEventFlagItemChangeOwner = 0x00004000,
   kFSEventStreamEventFlagItemXattrMod = 0x00008000,
   kFSEventStreamEventFlagItemIsFile = 0x00010000,
   kFSEventStreamEventFlagItemIsDir = 0x00020000,
   kFSEventStreamEventFlagItemIsSymlink = 0x00040000
};
"""

import os, datetime, time       # python packages
import fsevents                 # https://pypi.python.org/pypi/MacFSEvents
import Tkinter
import sys

# CONFIG PARAMS, set envirovnment variables or hardcode
# include trailing slashes for rsync, being more explicit is better
config = {
    'remote_host': 'user@remote.server.com',
    # try this if you are meeting non-standard ssh port
    # 'remote_host': "--rsh='ssh -p2222' user@remote.server.com",
    'watch': [
        {
            'local': '/your/local/path1/',
            'remote': '/remote/path1/'
        },
        {
            'local': '/your/local/path2/',
            'remote': '/remote/path2/'
        },
    ],
}

# list of files to ignore, simple substring match
ignore_list = ['.svn', '.DS_Store', '.git']

def display(str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mystr = "[{0}] {1} \n".format(now, str)
    print mystr


def file_event_sync(event):
    """ callback on event action, this does the sync passing in filename """
    filename = event.name
    local_path = None
    remote_path = None
    for watch in config['watch']:
        if filename.startswith(watch['local']):
            local_path = watch['local']
            remote_path = watch['remote']
    if local_path == None:
        display("[WARNING] can not found local path for file: %s" % filename)
        return
    remote_file = filename.replace(local_path, '')  # switch local path to remote
    for ig in ignore_list:                          # check ignore list
        if ig in filename:
            return

    kFSEventStreamEventFlagUserDropped = 0x00000002
    kFSEventStreamEventFlagMount = 0x00000040
    kFSEventStreamEventFlagItemCreated = 0x00000100
    kFSEventStreamEventFlagItemRemoved = 0x00000200

    if (event.mask & kFSEventStreamEventFlagItemCreated) != 0:
        # created
        remote_parent = os.path.dirname(remote_file)
        cmd = " rsync -cazq --delete %s %s:%s%s/ " % (filename, config['remote_host'], remote_path, remote_parent)
    elif (event.mask & kFSEventStreamEventFlagItemRemoved) != 0 or \
            (event.mask & kFSEventStreamEventFlagMount) != 0:
        # removed or renamed
        # no idea why kFSEventStreamEventFlagMount is for renaming
        local_parent = os.path.dirname(filename)
        remote_parent = os.path.dirname(remote_file)
        cmd = " rsync -cazq --delete %s/ %s:%s%s/ " % (local_parent, config['remote_host'], remote_path, remote_parent)
    elif (event.mask & kFSEventStreamEventFlagUserDropped) != 0:
        # modified
        # no idea why kFSEventStreamEventFlagUserDropped is for modifying
        cmd = " rsync -cazq --delete %s %s:%s%s " % (filename, config['remote_host'], remote_path, remote_file)
    else:
        display("[WARNING] Unsupported event: %s" % str(event))
        return

    display("Syncing %s" % filename)
    os.system(cmd)


## Main

if len(sys.argv) > 1 and sys.argv[1] == "--full":
    full_sync_matcher = None
    if len(sys.argv) > 2:
        full_sync_matcher = sys.argv[2]
    for watch in config['watch']:
        if full_sync_matcher != None and watch['local'].find(full_sync_matcher) == -1:
            continue
        print "Full sync from '%s' to %s:%s" % (watch['local'], config['remote_host'], watch['remote'])
        cmd = " rsync -cazqr --delete %s %s:%s " % (watch['local'], config['remote_host'], watch['remote'])
        print cmd
        os.system(cmd)
    exit(0)

## Setup Watcher
observer = fsevents.Observer()
for watch in config['watch']:
    stream = fsevents.Stream(file_event_sync, watch['local'], file_events=True)
    observer.schedule(stream)
    display("Watching: %s " % watch['local'])

observer.start()

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

## clean-up
observer.unschedule(stream)
observer.stop()
