'''
Created on Jul 30, 2012

@author: Arthur Valadares
'''

import common.helper
import csv
import json
import logging.config
import random
import signal
import socket
import threading
import time
import uuid
import websocket2 as websocket

global bot
global ws
bot = None
ws = None

MSG_FREQ = 5 # how many msgs per sec
FLUSH_FREQ = MSG_FREQ # flush to file every second
# we log all messages RTT

DISABLE_NAGLE = 1 # set to 0 to let Nagle's algorithm work 


class Bot():
    running = False
    measuring = False
    mypiece_id = None
    mypiece = None
    samples = 0
    measured_samples = 0

    pm_sent = {}
    delays = []

    def on_message(self, ws, message):
        """ Measure RTT for every message.
        Flush to file every once in a while. 
        """
        received_time = time.time()
        msg = json.loads(message)
        # Initial state
        if not self.running:
            if 'c' in msg:
                # open file and write header
                botname = "bot-" + str(uuid.uuid4())[:8]
                logging.info('Received config msg from server.')
                logging.info('My name is: %s' % botname)
                fname = botname + '.csv'
                logfile = open(fname, 'w', 0)
                self.logfile = logfile
                self.writer = csv.writer(logfile)
                header = ['botname', 'timestamp', 'rtt']
                #self.writer.writerow(header) # no need for header if cat dbg/bot-*.csv > all-bots.csv
                # start running the bot
                self.running = True
                self.start_game(msg['c'])
                # send my name to the server
                ws.send(json.dumps({'usr':botname}));
                self.botname = botname
                logging.info("Starting to measure RTT.")
                
        else: # msg for piece moved or dropped
            # check I sent this message
            if 'pm' in msg and msg['pm']['id'] == self.mypiece_id:
                pm_id = str(msg['pm']['x']) + ':' + str(msg['pm']['y'])
                if pm_id in self.pm_sent: 
                    sent_time = self.pm_sent[pm_id]
                    now = time.time()
                    delay = (received_time - sent_time) * 1000
                    self.delays.append((now, delay))
                    del self.pm_sent[pm_id]
                    # flush to file if quota reached
                    print '%d delays' % len(self.delays)
                    if len(self.delays) >= FLUSH_FREQ:
                        for tup in self.delays:
                            row = [self.botname, tup[0], tup[1]]
                            self.writer.writerow(row)
                        self.logfile.flush()
                        print 'flushed'
                        self.pm_sent = {}
                        self.delays = []
                    
    def on_error(self, ws, error):
        logging.exception("Exception in Bot handler:")

    def on_close(self, ws):
        self.running = False
        self.measuring = False
        print "### closed"

    def on_open(self, ws):
        self.running = False
        self.measuring = False
        print "### on_open"

    def start_game(self, cfg):
        self.imgset = cfg['img']
        self.board = cfg['board']
        self.grid = cfg['grid']
        self.dfrus = cfg['frus']
        self.pieces = cfg['pieces'] # maps piece id to piece
        self.myid = cfg['myid']
        self.imgurl = cfg['img']['img_url']
        threading.Thread(target=self.automate_bot, args=[ws]).start()

    def automate_bot(self, ws):
        """ Loop until self.running becomes False """
        x, y = 0, 0
        logging.info("Starting movement logic.")
        while self.running:
            # pick a piece that nobody has locked yet
            self.mypiece_id, self.mypiece = random.choice(self.pieces.items())
            while self.mypiece['l'] or self.mypiece['b']:
                self.mypiece_id, self.mypiece = random.choice(self.pieces.items())
            # start moving the piece around periodically
            while(self.running):
                while y + self.grid['cellh'] < self.board["h"]:
                    while x + self.grid['cellw'] < self.board["w"]:
                        pm_id = str(x) + ':' + str(y) # just to keep track of the messages I sent
                        self.pm_sent[pm_id] = time.time()
                        msg = {'pm' : {'id':self.mypiece_id,
                                       'x':x,
                                       'y':y}}
                        try:
                            ws.send(json.dumps(msg))
                        except AttributeError: # socket disappeared
                            break
                        time.sleep(1. / MSG_FREQ)
                        x += 10
                    x = 0
                    y += 10
                    logging.info('I am still moving the piece ...')
                y = 0
                x = 0

    def close(self):
        """ Send a piece drop message, then close the socket """
        msg = {'pd': {'id': self.mypiece_id,
                      'x': 50, # TODO: should drop where the piece was at
                      'y': 50,
                      'b': False}}
        ws.send(json.dumps(msg))
        self.logfile.close()
        ws.close()


def on_killed(signal, frame):
    """ When the user wants to kill the bot, just close the socket. """
    print 'You killed me'
    bot.close()


if __name__ == '__main__':
    # register signal handlers
    signal.signal(signal.SIGINT, on_killed)
    signal.signal(signal.SIGQUIT, on_killed)
    signal.signal(signal.SIGHUP, on_killed)

    # start bot
    bot = Bot()
    logging.config.fileConfig("bot_logging.conf")
    ip, port = common.helper.parse_bot_input()
    logging.info('[bot]: Connecting to %s:%s' % (ip, port))
    # set TCP_NODELAY to 1 to disable Nagle
    sockopt = ((socket.IPPROTO_TCP, socket.TCP_NODELAY, DISABLE_NAGLE),)
    ws = websocket.WebSocketApp("ws://" + ip + ":" + port + "/client",
                                on_message=bot.on_message,
                                on_error=bot.on_error,
                                on_close=bot.on_close,
                                sockopt=sockopt)
    ws.on_open = bot.on_open
    ws.run_forever()
