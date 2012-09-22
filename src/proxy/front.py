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
import proxy
from common.message import PROXY_DISTRIBUTION

temp_users = {}
clients = {}
client_proxy = {}
proxyref = None
proxy_options = None 
logger = logging.getLogger("proxy")

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
            print msg

class ClientHandler(tornado.websocket.WebSocketHandler):
    myid = None
    sticky_server=None
    
    def open(self):
        logger.debug("WebSocket opened")
        self.myid = str(uuid.uuid4())
        clients[self.myid] = self
        
        newmsg = {}
        newmsg["NU"] = [self.myid]
         
        
        if proxy_options["DISTRIBUTION"] == PROXY_DISTRIBUTION.STICKY:
            self.sticky_server = proxyref.back.sticky_server()
            newmsg["SS"] = proxyref.back.get_admid(self.sticky_server)
        proxyref.back.broadcast_admins(json.dumps(newmsg))
        
    def on_message(self, message):
        try:
            newmsg = {}
            # Append client metadata here. For now, just putting in the client's message and its uuid.
            newmsg["M"] = message
            newmsg["U"] = [self.myid]
            
            json_msg = json.dumps(newmsg)
            logger.debug(json_msg)
            proxyref.back.send_message_to_server(json_msg,self.sticky_server)
            
        except Exception:
            logger.exception('[Front]: Error processing message on Front module:')

    def on_close(self):
        newmsg = {}
        # User disconnected
        newmsg["UD"] = self.myid
        if self.sticky_server:
            newmsg["SS"] = proxyref.back.get_admid(self.sticky_server)

        proxyref.back.broadcast_admins(json.dumps(newmsg))
        logger.debug("WebSocket closed")
        
        
class ClientLayer(proxy.AbstractFront):
    dq = {}    
    def __init__(self, proxy,options):
        global proxyref
        global proxy_options
       
        logging.debug("Starting ClientLayer")
        proxyref = proxy
        proxy_options = options
        
    def send_message_to_client(self, message, clientList=None):
        remove_clients = []
        if clientList==None:
            clientList = clients
        logger.debug("[ClientLayer]: Sending " + str(message) + "to " + str(clientList))
        for client in clientList:
            if (client in clients):
                try:
                    clients[client].write_message(message)
                except IOError:
                    remove_clients.append(client)
                except AttributeError:
                    remove_clients.append(client)
            else:
                logger.warn("[Front]: Client " + client + " is not registered in this proxy.")
        for client in remove_clients:
            del clients[client]
            remove_clients = []
    
    def move_client(self,user,adm):
        if user in clients:
            clients[user].sticky_server = adm
            return True
        else:
            logger.warning("[front]: User " + str(user) + " is not connected here. Aborting...")
            return False
    
    def authorize_client(self, authclient, cuuid):
        clients[authclient] = temp_users[cuuid]
        
    def list_users(self):
        return clients.keys()
    