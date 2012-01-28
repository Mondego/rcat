import uuid
import tornado.web
import tornado.websocket
import time
import traceback
import Queue
import logging
from common.message import MESSAGE_TYPE
import json

temp_users = {}
clients = {}
proxyref = None

def SendToClient(handler,msg):
    handler.write(msg)

class HTTPHandler(tornado.web.RequestHandler):
    def get(self):
        SendToClient(self,"Hello World")
        
    def post(self):
        timestamp = time.time()
        argument = self.get_argument("message", False)
        if (argument):
            msg = argument + ";timestamp: " + str(timestamp)

class ClientHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        logging.debug("WebSocket opened")
        
    def on_message(self, message):
        global proxyref
        try:
            msg = json.loads(message)
            # Messages with "T" (for Type) are R-MUVE internal messages 
            if "T" in msg:
                if msg["T"] == MESSAGE_TYPE.CONNECT:
                    logging.info("CONNECTING")
                    temp_UUID = uuid.uuid4()
                    temp_users[unicode(temp_UUID)] = self
                    newmsg = {"T":MESSAGE_TYPE.CONNECT, "U":msg["U"], "TMP":unicode(temp_UUID)}
                    client_msg = json.dumps(newmsg)
            else:
                client_msg = message
            proxyref.send_message_to_server(client_msg)
            
        except Exception, err:
            logging.exception('[Front]: Error processing message on Front module:')

    def on_close(self):
        logging.debug("WebSocket closed")
        
        
class ClientLayer():
    dq = {}
    
    def __init__(self, proxy):
        global proxyref
        proxyref = proxy
        proxyref.send_message_to_client = self.send_message
        proxyref.authorize_client = self.authorize_client
        proxyref.test()
        
    def ClientConnect(self, userid):
        self.dq[userid] = Queue()
        
    def send_message(self, message, clientList=None):
        if clientList==None:
            clientList = clients
        for client in clientList:
            if (client in clients):
                clients[client].write_message(message)
            else:
                logging.warn("[Front]: Client " + client + " is not registered in this proxy.")
    
    def authorize_client(self, authclient, cuuid):
        clients[authclient] = temp_users[cuuid]
    