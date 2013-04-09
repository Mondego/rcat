"""
Front.py
Summary: Opens a websocket listener for servers. Messages from server are received in Front
and passed to Back so they can be delivered to client. Messages sent to Back are forwarded 
to Front through Proxy, in order to reach the server. 
"""
from common.message import PROXY_DISTRIBUTION
import json
import logging
import proxy
import socket
import time
import tornado.web
import tornado.websocket
import uuid
from collections import deque

temp_users = {}
clients = {}
client_proxy = {}
proxyref = None
proxy_options = None 
logger = logging.getLogger("proxy")
DISABLE_NAGLE = 0

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
        # set TCP_NODELAY to 1 to disable Nagle
        self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, DISABLE_NAGLE)

        self.myid = str(uuid.uuid4())
        clients[self.myid] = self
        proxyref.msg_queues[self] = deque() # queue of messages to send to this client handler
        
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
            #logger.debug(json_msg)
            proxyref.back.send_message_to_server(json_msg,self.sticky_server)
            
        except Exception:
            logger.exception('[Front]: Error processing message on Front module:')

    def on_close(self):
        newmsg = {}
        # User disconnected
        newmsg["UD"] = self.myid
        if self.sticky_server:
            newmsg["SS"] = proxyref.back.get_admid(self.sticky_server)

        try:
            del clients[self.myid]
        except:
            pass
        
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
        """ By default, broadcast the message to all clients """
        remove_clients = []
        if clientList==None:
            clientList = clients
        #logger.debug("[ClientLayer]: Sending " + str(message) + "to " + str(clientList))
        for clientid in clientList:
            if (clientid in clients):
                try:
                    handler = clients[clientid]
                    proxyref.msg_queues[handler].append(message)
                    #handler.write_message(message)
                except IOError:
                    remove_clients.append(clientid)
                except AttributeError:
                    remove_clients.append(clientid)
            else:
                logger.warn("[Front]: Client " + clientid + " is not registered in this proxy.")
        for clientid in remove_clients:
            del proxyref.msg_queues[clients[clientid]]
            del clients[clientid]
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
    
    def get_num_users(self):
        return len(clients)