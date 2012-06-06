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
import uuid

servers = []
admins = {}
sticky_client = {}
server_cycle = None
server_ref = None
proxyref = None
logger = logging.getLogger("proxy")

class ServerHandler(tornado.websocket.WebSocketHandler):    
    def open(self):
        global servers
        global server_cycle

        servers.append(self)
        server_cycle = itertools.cycle(servers)
                
    def on_message(self, message):
        try:
            msg = json.loads(message)
            logger.debug(message)
            if "U" in msg:
                users = msg["U"]
                logger.debug("Sending message " + msg["M"] + " to users " + str(users))
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
    admid = None
    def open(self):
        logger.debug("Admin Opened Connection")
        """
        self.admid = str(uuid.uuid4())

        newmsg = {"NS":[self.admid]}
        jsonmsg = json.dumps(newmsg)
        for adm in admins:
            adm.write_message(jsonmsg)
        admins[self.admid] = self
        """    
        
    def on_message(self, message):
        try:
            msg = json.loads(message)
            logger.debug(message)
            newmsg = {}
            
            # Internal requests
            ### List of Users - Request
            if "LUR" in msg:
                newmsg["NU"] = proxyref.front.list_users()
                json_newmsg = json.dumps(newmsg)
                self.write_message(json_newmsg)
            # Request list of servers
            elif "LSR" in msg:
                newmsg["LS"] = admins.keys()
                json_newmsg = json.dumps(newmsg)
                print json_newmsg
                self.write_message(json_newmsg)
            # Admin handler registers its UUID 
            elif "REG" in msg:
                self.admid = msg["REG"]
                admins[self.admid] = self
                if "REGBC" in msg:
                    newmsg = {"NS":[self.admid]}
                    jsonmsg = json.dumps(newmsg)
                    for adm in admins:
                        if adm != self:
                            adm.write_message(jsonmsg)
                    
            # Developer customized messages
            ### Broadcast messages to all admins
            elif "BC" in msg:
                proxyref.back.broadcast_admins(msg)
            # Forward message to specific server
            elif "FW" in msg:
                aid = msg["FW"]["ID"]
                msg["FW"] = msg["FW"]
                msg["FW"]["ID"] = self.admid
                json_newmsg = json.dumps(msg)
                admins[aid].write_message(json_newmsg)
                
        except Exception:
            logger.exception('[Back]: Error processing message on Back module:')
            
    def on_close(self):
        try:
            logger.debug("Admin Closed Connection")        
            del admins[self.admid]
        except Exception:
            logger.warning("[back]: Problem deleting admin from dictionary. Maybe it's already gone?")

class ServerLayer(proxy.AbstractBack):
    def __init__(self,proxy,options):
        global proxyref
        global serverlayer
        serverlayer = self
        logging.debug("Starting ServerLayer")
        proxyref = proxy
        
    def send_message_to_server(self,message,server=None):
        if (server):
            server.write_message(message)  
        elif len(servers) > 0:
            server_cycle.next().write_message(message)
            
    def sticky_server(self):
        return server_cycle.next()
    
    def broadcast_admins(self,message):
        for adm in admins.values():
            adm.write_message(message)
        