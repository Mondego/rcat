#!/usr/bin/python

import os
import sys
import time

f = open('proxies.lst','r')
proxies = f.read().splitlines()

if len(sys.argv) == 4:
    step = int(sys.argv[1])
    interval = int(sys.argv[2])
    total_bots = int(sys.argv[3])
    while (total_bots > 0):
        for proxy in proxies:
            add,port = proxy.split(':')
            print "Running %s bots on %s" % (step,proxy)
            os.system("./runbot.sh %s %s %s" % (add,port,step))
            total_bots -= step
            if total_bots <= 0:
                print "Finished launching all bots"
                sys.exit(0)
            print "Sleeping for %s seconds" % (interval)
            time.sleep(int(interval))

else:
    print "botlauncher.py {number of bots per proxy} {time interval}"

