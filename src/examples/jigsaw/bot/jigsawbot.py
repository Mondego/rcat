'''
Created on Jul 30, 2012

@author: Arthur Valadares
'''

from random import choice
import common.helper
import csv
import json
import logging.config
import os
import random
import signal
import sys
import threading
import time
import uuid
import websocket

global bot
global ws
bot = None
ws = None

freq = 10 # how many msgs per sec
TOTAL_NUM_SAMPLES = 1 # how many msgs in a row to measure the RTT
MIN_SAMPLE_DELAY = 1 # in seconds, minimum amount of time between 2 groups of measurements
# this is also the maximum measurable RTT

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
                logfile = open(fname, 'w', 0) # TODO: WHERE IS THAT FILE???
                self.logfile = logfile
                self.writer = csv.writer(logfile)
                header = ['botname', 'timestamp', 'rtt']
                self.writer.writerow(header)
                # start running the bot
                self.running = True
                self.start_game(msg['c'])
                # send my name to the server
                ws.send(json.dumps({'usr':botname}));
                self.botname = botname
                self.log_timer = threading.Timer(5, self.measure_timer)
                self.log_timer.daemon = True
                self.log_timer.start()
        else:
            if self.measuring and self.measured_samples > 0:
                if 'pm' in msg:
                    if msg['pm']['id'] == self.mypiece_id:
                        ident = str(msg['pm']['x']) + ':' + str(msg['pm']['y'])
                        if ident in self.pm_sent:
                            self.measured_samples -= 1
                            sent_time = self.pm_sent[ident]
                            now = time.time()
                            delay = (received_time - sent_time) * 1000
                            self.delays.append((now, delay))
                            del self.pm_sent[ident]

                            if self.measured_samples < 0:
                                self.measuring = False

    def measure_timer(self):
        """ Measure 10 samples in a row every 10 to 15 seconds. 
        Flush to file. """
        logging.info("Starting to measure.")
        while True:
            self.samples = TOTAL_NUM_SAMPLES
            self.measured_samples = TOTAL_NUM_SAMPLES
            self.measuring = True
            # 10 Seconds max of measurement before stopping
            time.sleep(MIN_SAMPLE_DELAY)
            self.measuring = False
            for tup in self.delays:
                row = [self.botname, tup[0], tup[1]]
                self.writer.writerow(row)
            self.logfile.flush()
            self.pm_sent = {}
            self.delays = []
            #time.sleep(random.randrange(0, 1))
            time.sleep(1)

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
            self.mypiece_id, self.mypiece = choice(self.pieces.items())
            while self.mypiece['l'] or self.mypiece['b']:
                self.mypiece_id, self.mypiece = choice(self.pieces.items())
            # start moving the piece around periodically
            while(self.running):
                while y + self.grid['cellh'] < self.board["h"]:
                    while x + self.grid['cellw'] < self.board["w"]:
                        if self.measuring:
                            if self.samples > 0:
                                self.pm_sent[str(x) + ':' + str(y)] = time.time()
                                self.samples -= 1
                        msg = {'pm' : {'id':self.mypiece_id,
                                       'x':x,
                                       'y':y}}
                        try:
                            ws.send(json.dumps(msg))
                        except AttributeError: # socket disappeared
                            break
                        time.sleep(1. / freq)
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
    ws = websocket.WebSocketApp("ws://" + ip + ":" + port + "/client",
                                on_message=bot.on_message,
                                on_error=bot.on_error,
                                on_close=bot.on_close)
    ws.on_open = bot.on_open
    ws.run_forever()
