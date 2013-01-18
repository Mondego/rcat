'''
Created on Jul 30, 2012

@author: Arthur Valadares
'''

import websocket
import json
import threading
import time
import common.helper
import logging
import logging.config

class Bot():
    running = False
    def on_message(self,ws, message):
        logging.info(message);
        msg = json.loads(message)
        if 'c' in msg:
            self.start_game(msg['c'])
        """
        elif 'pm' in msg:
            id = msg['pm']['id']
            x = msg['pm']['x']
            y = msg['pm']['y']
            owner = msg['pm']['l']
            # TODO: finish
        elif 'pd' in msg:
            id = msg['pd']['id']
            x = msg['pd']['x']
            y = msg['pd']['y']
            owner = msg['pd']['l']
            # TODO: finish
        """
    
    def on_error(self,ws, error):
        logging.exception("[jigsawbot]: Exception in Bot handler:")
    
    def on_close(self,ws):
        pass
    
    def on_open(self,ws):
        self.running = True
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
        logging.info("[bot: Starting bot....")
        while self.running:
            for v in self.pieces.values():
                if not v['l'] or v['l'] == "None":
                    while y < self.board["h"]:
                        while x < self.board["w"]:
                            ws.send(self.move_piece(v,x,y))
                            time.sleep(0.1)
                            x += 5
                        x = 0
                        y += 5
                    

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