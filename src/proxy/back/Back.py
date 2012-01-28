import json
import tornado.websocket
from common.message import MESSAGE_TYPE
import itertools
import logging
import traceback

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
        global proxyref
        try:
            msg = json.loads(message)
            if "T" in msg:
                if msg["T"] == MESSAGE_TYPE.ACCEPTED:
                    print "Client authentication accepted."
                    proxyref.authorize_client(msg["U"],msg["TMP"])
            else:
                if "U" in msg:
                    users = msg["U"]
                    proxyref.send_message_to_client(msg["M"],users)
                else:
                    proxyref.send_message_to_client(msg["M"])
        except Exception,err:
            logging.exception('[Back]: Error processing message on Back module:')
            
    def on_close(self):
        global servers
        global server_cycle
        
        logging.debug("WebSocket closed")
        servers.remove(self)
        server_cycle = itertools.cycle(servers)

class ServerLayer():
    def __init__(self,proxy):
        global proxyref
        logging.debug("Starting ServerLayer")
        proxyref = proxy
        proxyref.send_message_to_server = self.send_message
        
    def send_message(self,message):
        global server_cycle
        global servers
        
        if len(servers) > 0:
            server_cycle.next().write_message(message)
        