"""
Back.py
Summary: Opens a websocket listener for clients. Messages sent to Back are forwarded 
to Front through Proxy, in order to reach the server. 
Messages from server are received in Front, and passed to Back so they can be delivered to client.
"""
import json
import tornado.websocket
import itertools
import logging
import proxy

servers = []
admins = []
sticky_client = {}
server_cycle = None
admins_cycle = None
proxyref = None
logger = logging.getLogger("proxy")

class ServerHandler(tornado.websocket.WebSocketHandler):    
    def open(self):
        global servers
        global server_cycle

        servers.append(self)
        server_cycle = itertools.cycle(servers)
                
    def on_message(self, message):
        global proxyref
        try:
            msg = json.loads(message)
            logger.debug(message)
            if "U" in msg:
                users = msg["U"]
                logger.debug("Sending message " + msg["M"] + "to users " + str(users))
                proxyref.front.send_message_to_client(msg["M"],users)
            else:
                proxyref.front.send_message_to_client(msg["M"])
        except Exception:
            logger.exception('[Back]: Error processing message on Back module:')
            
    def on_close(self):
        global servers
        global server_cycle
        
        servers.remove(self)
        server_cycle = itertools.cycle(servers)
        
class AdminHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        logger.debug("Admin Opened Connection")
        admins.append(self)
        newmsg = {}
        newmsg["LU"] = proxyref.front.list_users()
        self.write_message(json.dumps(newmsg))
        
    def on_message(self, message):
        global proxyref
        try:
            msg = json.loads(message)
            logger.debug(message)
            # List of Users - Request
            if "LUR" in msg:
                newmsg = {}
                newmsg["LU"] = proxyref.front.list_users()
                self.write_message(json.dumps(newmsg))
        except Exception:
            logger.exception('[Back]: Error processing message on Back module:')
            
    def on_close(self):
        logger.debug("Admin Closed Connection")        
        admins.remove(self)

class ServerLayer(proxy.AbstractBack):
    def __init__(self,proxy,options):
        global proxyref
        logging.debug("Starting ServerLayer")
        proxyref = proxy
        
    def send_message_to_server(self,message,server=None):
        global server_cycle
        global servers
        
        if (server):
            server.write_message(message)  
        elif len(servers) > 0:
            server_cycle.next().write_message(message)
            
    def sticky_server(self):
        global server_cycle
        global servers
        
        return server_cycle.next()
    
    def broadcast_admins(self,message):
        for adm in admins:
            adm.write_message(message)
        