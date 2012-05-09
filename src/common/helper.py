import time
import sys
import socket
import fcntl
import struct
import argparse
import os
import ConfigParser
import logging

ansi_codes = {
               "blue" : '\033[94m',
               "green" : '\033[92m',
               "yellow" : '\033[93m',
               "endc" : '\033[0m'
              }

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
    
def parse_input(cfg_file='app.cfg'):
    myip,myport,fp,cfg = None,None,None,cfg_file
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', help='port', default='9999')
    parser.add_argument('-ip', help='host')
    parser.add_argument('-c', help='configuration file', default=cfg)

    args = vars(parser.parse_args()) # returns a namespace converted to a dict)
    
    if args['ip'] and args['p']:
            myip = args['ip']
            myport = args['p']
    else:        
        if 'c' in args:
            cfg = args['c']
        
        if (os.path.isfile(cfg)):
            fp = open(cfg)
        elif os.path.isfile(os.getenv("HOME") + '/.rcat/' + cfg):
            fp = open(os.getenv("HOME") + '/.rcat/' + cfg)            
        config = ConfigParser.ConfigParser()
        if fp:
            try:
                config.readfp(fp)
                myip = config.get('Main', 'host')
                myport = config.get('Main', 'port')
            except IOError as e:
                logging.error("[mysqlconn]: Could not open file. Exception: ",e)
                myip = get_ip_address('eth0')
        else:
            return False
        
    if myip and myport:
        return myip,myport
    else:
        return False

def printc(msg,color):
    print ansi_codes[color] + msg + ansi_codes["endc"] 
    
def terminal():
    time.sleep(2)
    printc("\n\nInput commands to RCAT below. Type help for list for commands.","blue")
    while(1):
        sys.stdout.write(ansi_codes["green"] + "[rcat]: ")
        line = sys.stdin.readline()
        if line.startswith("quit"):
            printc("Quitting RCAT....","yellow")
            sys.exit(0)
        if line.startswith("help"):
            print "quit: (Force) quits RCAT"