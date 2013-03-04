from threading import Lock
import ConfigParser
import argparse
import json
import logging
import os
import sys

paths = {}

ansi_codes = {
               "blue" : '\033[94m',
               "green" : '\033[92m',
               "yellow" : '\033[93m',
               "endc" : '\033[0m'
              }

#===============================================================================
#import socket
#import struct
#import time
#import fcntl
# def get_ip_address(ifname):
#    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#    return socket.inet_ntoa(fcntl.ioctl(
#        s.fileno(),
#        0x8915, # SIOCGIFADDR
#        struct.pack('256s', ifname[:15])
#    )[20:24])
#===============================================================================

def parse_input(cfg_file='app.cfg'):
    myip, myport, fp, cfg = None, None, None, cfg_file
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', help='port', default='9999')
    parser.add_argument('-ip', help='host')
    parser.add_argument('-c', help='configuration file', default=cfg)
    parser.add_argument('-prx', help='list of proxies', default='["ws://localhost:8888"]')

    settings = {}
    args = vars(parser.parse_args()) # returns a namespace converted to a dict)
    config = None

    if args['ip'] and args['p']:
            myip = args['ip']
            myport = args['p']
            proxies = json.loads(args['prx'])
    else:
        if 'c' in args:
            cfg = args['c']

        if (os.path.isfile(cfg)):
            fp = open(cfg)
        elif os.path.isfile(os.getenv("HOME") + '/.rcat/' + cfg):
            fp = open(os.getenv("HOME") + '/.rcat/' + cfg)
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        if fp:
            try:
                config.readfp(fp)
                myip = config.get('Main', 'apphost')
                myport = config.get('Main', 'appport')
                proxies = json.loads(config.get('Main', 'proxies'))
                persist_timer = config.get('Main', 'persist_timer')
                plugins = config.get('Main', 'plugins').split(',')
            except IOError as e:
                logging.error("[mysqlconn]: Could not open file. Exception: ", e)
                #myip = get_ip_address('eth0')
        else:
            return {}

    if myip and myport:
        settings['ip'] = myip
        settings['port'] = myport
        settings['proxies'] = proxies
        settings['persist_timer'] = int(persist_timer)
        settings['plugins'] = plugins
        return settings
    else:
        return {}

def parse_bot_input():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', help='port', default='8888')
    parser.add_argument('-ip', help='host', default='localhost')
    args = vars(parser.parse_args())
    return args["ip"], args["p"]


def open_configuration(path):
    if (os.path.isfile(path)):
        fp = open(path)
    elif os.path.isfile(os.getenv("HOME") + '/.rcat/' + path):
        fp = open(os.getenv("HOME") + '/.rcat/' + path)
    else:
        return None
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.readfp(fp)
    paths[path] = fp
    return config

def close_configuration(path):
    paths[path].close()
    del paths[path]
    return True

def printc(msg, color):
    print ansi_codes[color] + msg + ansi_codes["endc"]

class Terminal():
    lock = None
    app = None

    def __init__(self, app):
        self.lock = Lock()
        self.lock.acquire()
        self.app = app
        self.app.debug_print = lambda cmd: eval(cmd)

    def show_terminal(self):
        if self.lock.locked():
            self.lock.release()

    def pause_terminal(self):
        if not self.lock.locked():
            self.lock.acquire()

    def run_terminal(self):
        with self.lock:
            printc("\n\nInput commands to RCAT below. Type help for list for commands.", "blue")
        while(1):
            self.lock.acquire()
            sys.stdout.write(ansi_codes["green"] + "[rcat]: ")
            line = sys.stdin.readline()
            if line.startswith("quit"):
                printc("Quitting RCAT....", "yellow")
                sys.exit(0)
            if line.startswith("help"):
                printc("quit: (Force) quits RCAT\nprint arg: Runs a 'print arg' in the application. Application represented by 'app' (e.g. print app)", "endc")
            if line.startswith("restart"):
                self.app.declare_game_end()
            if line.startswith("print"):
                try:
                    cmd = line.split()
                    if len(cmd) > 2:
                        logging.warn("Only one variable at a time.")
                    else:
                        app = self.app
                        print eval(cmd[1])
                except Exception, e:
                    logging.error("Could not read variable.")
                    print e
            self.show_terminal()
