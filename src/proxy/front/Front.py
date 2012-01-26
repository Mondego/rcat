import sys
import uuid
import tornado.web
import tornado.websocket
import time
import traceback
import Queue
import logging
from multiprocessing import Process
from common.message import MESSAGE_TYPE
import json

temp_users = {}
client = {}
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
                    temp_users[temp_UUID] = [msg["U"], self]
                    newmsg = {"T":MESSAGE_TYPE.CONNECT, "U":msg["U"], "TMP":temp_UUID}
                    client_msg = json.dumps(newmsg)
            else:
                client_msg = message
            proxyref.send_message_to_server(client_msg)
            
        except Exception, err:
            traceback.print_exc()

    def on_close(self):
        logging.debug("WebSocket closed")
        
    def accept_client(self,client_id, old_id):
        #TODO: Warn Application Layer that client with this name already exists
        # temp_users[old_id][1] is the handler for this client
        client[client_id] = temp_users[old_id][1]
        del temp_users[old_id]
        
        
class ClientLayer():
    dq = {}
    
    def __init__(self, proxy):
        global proxyref
        #p = Process(target=SendLoop, args=(self.dq,))
        #p.start()
        proxyref = proxy
        proxyref.send_message_to_client = self.send_message
        proxyref.test()
        
    def ClientConnect(self, userid):
        self.dq[userid] = Queue()
        
    def send_message(self, message, clients):
        pass

def SendLoop(dq):
    for client in dq:
        #Send message to client
        pass
