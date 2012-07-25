import ConfigParser
import argparse
import os
import time
import sys
import subprocess
from tempfile import mkstemp

VERSION = 0
RCAT_ROOT = "../../"

parser = argparse.ArgumentParser()
parser.add_argument('-f', help='file with list of servers. Organized by external hostname, proxy, app', default='config_hosts')
parser.add_argument('-a', help='application to be deployed', default='jigsaw')

args = vars(parser.parse_args()) # returns a namespace converted to a dict)

def configure_servers(servers):
    # Check if servers are configured. 
    for tuples in servers:
        if tuples != '':
            if tuples[0].count('@') == 0:
                tuples[0] = "mondego@" + tuples[0]
            try:
                cmd = "ssh " + tuples[0] + " \'cat ~/rcat/VERSION\'"
                res = subprocess.check_output(cmd,shell=True)
                print res
                if res.count('RCAT_VERSION') == 0:
                    configure_server(tuples[0])
                else:
                    if int(res.split('=')[1]) < VERSION:
                        configure_server(tuples[0])
            except Exception,e:
                print e
                configure_server(tuples[0])

def configure_server(hostname):
    os.system("ssh " + hostname + " \'mkdir ~/rcat\'")
    os.system("scp -rp " + RCAT_ROOT + "* " +  hostname + ":~/rcat")
    os.system("ssh " + hostname + " \'echo RCAT_VERSION=" + str(VERSION) + " > ~/rcat/VERSION; cd ~/rcat/test/deploy; bash ./configure_server.sh\'")

def readlines(path):
    if (os.path.isfile(path)):
        fpp = open(path)
        listservers = fpp.read().splitlines()
        servers = []
        for item in listservers:
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
            cmd = "scp /tmp/rcat.cfg " + tuples[0] + ":~/rcat/test/"
            print cmd
            os.system(cmd) 
    
def start_apps(servers):
    template_file = open("/tmp/rcat.cfg")
    for tuples in servers:
        if tuples[2]:
            apphost,appport = tuples[2].split(':')
            fh, abs_path = mkstemp()
            new_file = open(abs_path,'w')
            
            for line in template_file:
                if line.count('!!!'):
                    new_file.write(line.replace('!!!',apphost))
                elif line.count('@@@'):
                    new_file.write(line.replace('@@@',appport))
                else:
                    new_file.write(line)
            print abs_path
            new_file.close()
            os.system("scp " + abs_path + " " + tuples[0] + ":~/rcat/test/rcat.cfg")            
            
    template_file.close()

s = readlines(args['f']) 
    
configure_servers(s)
listp = start_proxies(s)
start_apps(s)

def launch_proxies(servers):
    for tuples in servers:
        if tuples[1]:
            print "Starting proxy in " + tuples[0]
            cmd = "ssh " + tuples[0] + " \'screen -d -m ./rcat/test/runproxy.sh\'"
            os.system(cmd)

time.sleep(2)

def launch_apps(servers):
    appname = args['a']
    for tuples in servers:
        if tuples[2]:
            print "Starting app in " + tuples[0]
            cmd = "ssh " + tuples[0] + " \'cp ~/rcat/test/deploy/configs/" + appname + ".cfg ~/rcat/test \'"
            os.system(cmd)       
            cmd = "ssh " + tuples[0] + " \'screen -d -m ./rcat/test/run" + appname + ".sh\'"
            os.system(cmd)

launch_proxies(s)
launch_apps(s)
# Now setup config files for proxy and app! .......

