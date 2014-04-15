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

"""
import os, datetime, time       # python packages
import fsevents                 # https://pypi.python.org/pypi/MacFSEvents
import Tkinter

# CONFIG PARAMS, set envirovnment variables or hardcode
# include trailing slashes for rsync, being more explicit is better
config = {
    'remote_host': 'user@remote.server.com',
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
    global ta
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mystr = "[{0}] {1} \n".format(now, str)
    ta.insert(Tkinter.END, mystr)


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
    
    # basic rsync to remote server
    cmd = " rsync -cazq --del %s %s:%s%s " % (filename, config['remote_host'], remote_path, remote_file)
    display("Syncing %s " % filename)
    os.system(cmd)


## Main

## Setup GUI
canvas = Tkinter.Tk()
scroll = Tkinter.Scrollbar(canvas)
ta = Tkinter.Text(canvas)

scroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
ta.pack(side=Tkinter.LEFT, fill=Tkinter.Y)
scroll.config(command=ta.yview)
ta.config(yscrollcommand=scroll.set)

## Setup Watcher
observer = fsevents.Observer()
observer.start()
for watch in config['watch']:
    stream = fsevents.Stream(file_event_sync, watch['local'], file_events=True)
    observer.schedule(stream)
    display("Watching: %s " % watch['local'])

## running
canvas.mainloop()

## clean-up
observer.unschedule(stream)
observer.stop()
