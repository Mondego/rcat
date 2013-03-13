#!/usr/bin/python

import ConfigParser
import argparse
import os
import time
import sys
import subprocess
from tempfile import mkstemp

VERSION = 0
RCAT_ROOT = "../../"
STDRCAT = "rcat"

def configure_servers(servers):
    # Check if servers are configured. 
    for tuples in servers:
        if tuples != '':
            if tuples[0].count('@') == 0:
                tuples[0] = "mondego@" + tuples[0]
            if tuples[4]:
                # If folder is specified, make sure everything resides under STDRCAT
                tuples[4] = STDRCAT + '/' + tuples[4]
            else:
                # Else, just use the standard "rcat" name
                tuples[4] = STDRCAT
            try:
                cmd = "ssh %s \'cat ~/%s/VERSION\'" % (tuples[0],tuples[4])
                res = subprocess.check_output(cmd,shell=True)
                print res
                if res.count('RCAT_VERSION') == 0:
                    configure_server(tuples[0],tuples[4])
                else:
                    if int(res.split('=')[1]) < VERSION:
                        configure_server(tuples[0],tuples[4])
            except Exception,e:
                print e
                configure_server(tuples[0],tuples[4])

def configure_server(hostname,dest_folder):
    # Creates rcat and bin folder
    os.system("ssh %s \'mkdir -p ~/%s\'" % (hostname,dest_folder))
    # Copies all files in src folder to destination root folder (to avoid copying git files)
    # os.system("scp -rp %s* %s:~/%s" % (RCAT_ROOT,hostname,dest_folder))
    # Creates the static folder, that will host the html files
    # os.system("scp -rp %s %s:~/%s/bin/static" % (STATIC,hostname,dest_folder))
    os.system("rsync -rav --exclude \'*.git\' --exclude \'dbg/results\' %s %s:~/%s" % (RCAT_ROOT,hostname,dest_folder))
    # Copy .conf files for logging (proxy_logging.conf, connector_logging.conf)
    os.system("ssh %s \'cp ~/%s/dbg/deploy/configs/*.conf ~/%s/bin\'" % (hostname,dest_folder,dest_folder))
    # Sets the RCAT version and attempts to install all necessary libraries
    os.system("ssh %s \'echo RCAT_VERSION=%s > ~/%s/VERSION; cd ~/%s/dbg/deploy; bash ./configure_server.sh\'" % (hostname,str(VERSION),dest_folder,dest_folder))

def readlines(path):
    if (os.path.isfile(path)):
        fpp = open(path)
        listservers = fpp.read().splitlines()
        servers = []
        for item in listservers:
            if not item.startswith('#'):
                data = item.split(',')
                if data[0]:
                    servers.append(data)
        
        fpp.close()
        return servers
    else:
        sys.exit("file " + path + " could not be found.")
    
def start_proxies(servers):
    # servers = list of lists of external hostname, proxy, app
    print servers
    proxy_list = "["
    for tuples in servers:
        if tuples[1]:
            proxy_list += "\"ws://" + tuples[1] + "\","
    proxy_list = proxy_list.rstrip(',') + ']'
    print proxy_list

    f = open("./configs/rcat.cfg.temp")
    newf = open('/tmp/rcat.cfg','w')

    for line in f:
        newf.write(line.replace('###',proxy_list))

    f.close()
    newf.close()
    
    for tuples in servers:
        if tuples[1]:
            cmd = "scp /tmp/rcat.cfg %s:~/%s/bin" % (tuples[0],tuples[4])
            print cmd
            os.system(cmd) 
    
def start_apps(servers):
    template_file = open("/tmp/rcat.cfg")
    template_lines = template_file.readlines()
    template_file.close()
    for tuples in servers:
        if tuples[2]:
            apphost,appport = tuples[2].split(':')
            fh, abs_path = mkstemp()
            new_file = open(abs_path,'w')
            
            for line in template_lines:
                if line.count('!!!'):
                    new_file.write(line.replace('!!!',apphost))
                elif line.count('@@@'):
                    new_file.write(line.replace('@@@',appport))
                else:
                    new_file.write(line)
            # print abs_path
            new_file.close()
            # Copy rcat.cfg
            os.system("scp %s %s:~/%s/bin/rcat.cfg" % (abs_path,tuples[0],tuples[4]))

# Check for tuples[4]
def launch_proxies(servers):
    for tuples in servers:
        if tuples[1]:
            print "Starting proxy in " + tuples[0]
            host,port = tuples[1].split(':')
            cmd = "ssh %s \'cd ~/%s/bin; screen -d -m ./runproxy.sh %s --benchmark\'" % (tuples[0],tuples[4],port)
            print cmd
            os.system(cmd)

def launch_apps(servers):
    appname = args['a']
    for tuples in servers:
        if tuples[2]:
            print "Starting app in " + tuples[0]
            cmd = "ssh %s \'cp ~/%s/dbg/deploy/configs/%s ~/%s/bin/%s.cfg\'" % (tuples[0],tuples[4],tuples[3],tuples[4],appname)
            print cmd
            os.system(cmd)
            cmd = "ssh %s \'cd ~/%s/bin; screen -d -m ./run%s.sh\'" % (tuples[0],tuples[4],appname)
            print cmd
            os.system(cmd)
            time.sleep(1)


if __name__=="__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', help='file with list of servers. Organized by external hostname, proxy, app', default='./configs/config_hosts')
        parser.add_argument('-a', help='application to be deployed', default='jigsaw')

        args = vars(parser.parse_args()) # returns a namespace converted to a dict)

        s = readlines(args['f'])

        configure_servers(s)
        start_proxies(s)
        start_apps(s)

        launch_proxies(s)
        time.sleep(2)
        launch_apps(s)
        # Now setup config files for proxy and app! .......

