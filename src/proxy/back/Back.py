import json
import tornado.web
import tornado.websocket
from common.message import MESSAGE_TYPE
import itertools
import logging

servers = []
server_cycle = None
proxyref = None

class ServerHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        global servers
        global server_cycle
        
        logging.debug("WebSocket opened")
        servers.append(self)
        server_cycle = itertools.cycle(servers)
        
    def on_message(self, message):
        try:
            msg = json.loads(message)
            if msg["type"] == MESSAGE_TYPE.ACCEPTED:
                print "Client authentication accepted."
                
            
        except Exception as inst:
            self.write_message("Not valid JSON")
            print inst

    def on_close(self):
        global servers
        global server_cycle
        
        logging.debug("WebSocket closed")
        servers.remove(self)
        server_cycle = itertools.cycle(servers)

class ServerLayer():
    def __init__(self,proxy):
        logging.debug("Starting ServerLayer")
        proxyref = proxy
        proxyref.send_message_to_server = self.send_message
        
    def send_message(self,message):
        global server_cycle
        global servers
        
        if len(servers) > 0:
            server_cycle.next().write_message(message)
        