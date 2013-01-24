'''
Created on Jul 30, 2012

@author: Arthur Valadares
'''

from random import choice
from threading import Timer
import common.helper
import json
import logging.config
import random
import threading
import time
import websocket

global bot
bot = None

class Bot():
    running = False
    measuring = False
    mypiece = None
    samples = 0
    measured_samples = 0
    
    pm_sent = {}
    delays = []
    
    def on_message(self,ws, message):
        msg = json.loads(message)
        if not self.running:
            if 'c' in msg:
                Timer(5,self.measure_timer).start()
		self.running = True
		self.botname = "bot" + str(random.randrange(0,99999))
		#self.botname = 'Guest'
		ws.send(json.dumps({'usr':'Guest'}));
                self.start_game(msg['c'])
                
        if self.measuring and self.measured_samples > 0:
            if 'pm' in msg:
                if (str(msg['pm']['x']) + str(msg['pm']['y'])) in self.pm_sent:
                    self.measured_samples -= 1
                    received_time = time.time()
                    sent_time = self.pm_sent[str(msg['pm']['x']) + str(msg['pm']['y'])]
                    self.delays.append(received_time-sent_time)
                    
                    if self.measured_samples < 0:
                        self.measuring = False
                    
    def measure_timer(self):
	logging.info("[bot]: Starting to measure")
        while True:
            self.samples = 10
            self.measured_samples = 10
            self.measuring = True
            # 10 Seconds max of measurement before stopping
            time.sleep(10)
            self.measuring = False
            self.pm_sent = {}
            logging.info(self.delays)
            self.delays = []
            time.sleep(random.randrange(5,20))
    
    def on_error(self,ws, error):
        logging.exception("[bot]: Exception in Bot handler:")
    
    def on_close(self,ws):
        self.running = False
        self.measuring = False
        print "### closed"
    
    def on_open(self,ws):
        self.running = False
        self.measuring = False
        print "### on_open"
    
    def start_game(self,cfg):
        self.imgset = cfg['img']
        self.board = cfg['board']
        self.grid = cfg['grid']
        self.dfrus = cfg['frus']
        self.pieces = cfg['pieces']
        self.myid = cfg['myid']
        self.imgurl = cfg['img']['img_url']
        threading.Thread(target=self.automate_bot,args=[ws]).start()
        
    def automate_bot(self,ws):
        x,y = 0,0
        logging.info("[bot]: Starting bot....")
        while self.running:
            v = choice(self.pieces.values())
            if not v['l'] or v['l'] == "None":
                self.mypiece = v['pid']
                while(self.running):
                    while y < self.board["h"]:
                        while x < self.board["w"]:
                            ws.send(self.move_piece(v,x,y))
                            if self.measuring:
                                if self.samples > 0:
                                    self.pm_sent[str(x)+str(y)] = time.time()
                                    self.samples -= 1
                            time.sleep(0.05)
                            x += 5
                        x = 0
                        y += 5
                    y = 0
                    x = 0
                    

    def move_piece(self,p,x,y):
        msg = {'pm' : {'id':p["pid"], 'x':x,'y':y}}
        jsonmsg = json.dumps(msg)

        return jsonmsg

if __name__ == '__main__':
    bot = Bot()
    logging.config.fileConfig("bot_logging.conf") 
    ip,port = common.helper.parse_bot_input()
    logging.info('[bot]: Connecting to %s:%s' % (ip,port))
    ws = websocket.WebSocketApp("ws://" + ip + ":" + port + "/client",
                                on_message = bot.on_message,
                                on_error = bot.on_error,
                                on_close = bot.on_close)
    ws.on_open = bot.on_open
    ws.run_forever()
