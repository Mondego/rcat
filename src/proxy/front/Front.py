"""
Front.py
Summary: Opens a websocket listener for servers. Messages from server are received in Front
and passed to Back so they can be delivered to client. Messages sent to Back are forwarded 
to Front through Proxy, in order to reach the server. 
"""
import json
import logging
import time
import tornado.web
import tornado.websocket
import uuid
from common.message import PROXY_DISTRIBUTION

temp_users = {}
clients = {}
client_proxy = {}
proxyref = None
proxy_options = None 

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
    logger = logging.getLogger("proxy")
    myid = None
    sticky_server=None
    
    def open(self):
        global proxy_options
        
        self.logger.debug("WebSocket opened")
        self.myid = str(uuid.uuid4())
        clients[self.myid] = self
        
        newmsg = {}
        newmsg["NU"] = self.myid 
        
        if proxy_options["DISTRIBUTION"] == PROXY_DISTRIBUTION.STICKY:
            self.sticky_server = proxyref.sticky_server()
        proxyref.broadcast_admins(json.dumps(newmsg))
        
    def on_message(self, message):
        global proxyref
        global proxy_options
        try:
            newmsg = {}
            # Append client metadata here. For now, just putting in the client's message and its uuid.
            newmsg["M"] = message
            newmsg["U"] = [self.myid]
            
            json_msg = json.dumps(newmsg)
            self.logger.debug(json_msg)
            proxyref.send_message_to_server(json_msg,self.sticky_server)
            
        except Exception, err:
            self.logger.exception('[Front]: Error processing message on Front module:')

    def on_close(self):
        newmsg = {}
        # User disconnected
        newmsg["UD"] = self.myid

        proxyref.broadcast_admins(json.dumps(newmsg))
        self.logger.debug("WebSocket closed")
        
        
class ClientLayer():
    dq = {}
    logger = logging.getLogger("proxy")
    
    def __init__(self, proxy,options):
        global proxyref
        global proxy_options
       
        proxyref = proxy
        proxy_options = options
        proxyref.send_message_to_client = self.send_message
        proxyref.authorize_client = self.authorize_client
        proxyref.list_users = self.list_users
        proxyref.test()
        
    def send_message(self, message, clientList=None):
        if clientList==None:
            clientList = clients
        self.logger.debug("[ClientLayer]: Sending " + str(message) + "to " + str(clientList))
        for client in clientList:
            if (client in clients):
                clients[client].write_message(message)
            else:
                self.logger.warn("[Front]: Client " + client + " is not registered in this proxy.")
    
    def authorize_client(self, authclient, cuuid):
        clients[authclient] = temp_users[cuuid]
        
    def list_users(self):
        return clients
    