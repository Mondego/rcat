import json
import tornado.websocket
import itertools
import logging
import traceback

servers = []
admins = []
server_cycle = None
admins_cycle = None
proxyref = None

class ServerHandler(tornado.websocket.WebSocketHandler):
    logger = logging.getLogger("proxy")
    def open(self):
        global servers
        global server_cycle

        servers.append(self)
        server_cycle = itertools.cycle(servers)
                
    def on_message(self, message):
        global proxyref
        try:
            msg = json.loads(message)
            self.logger.debug(message)
            if "U" in msg:
                users = msg["U"]
                self.logger.debug("Sending message " + msg["M"] + "to users " + str(users))
                proxyref.send_message_to_client(msg["M"],users)
            else:
                proxyref.send_message_to_client(msg["M"])
        except Exception,err:
            self.logger.exception('[Back]: Error processing message on Back module:')
            
    def on_close(self):
        global servers
        global server_cycle
        
        servers.remove(self)
        server_cycle = itertools.cycle(servers)
        
class AdminHandler(tornado.websocket.WebSocketHandler):
    logger = logging.getLogger("proxy")
    def open(self):
        self.logger.debug("Admin Opened Connection")
        admins.append(self)
        newmsg = {}
        newmsg["LU"] = proxyref.list_users()
        self.write_message(json.dumps(newmsg))
        
    def on_message(self, message):
        global proxyref
        try:
            msg = json.loads(message)
            self.logger.debug(message)
            # List of Users - Request
            if "LUR" in msg:
                newmsg = {}
                newmsg["LU"] = proxyref.list_users()
                self.write_message(json.dumps(newmsg))
        except Exception,err:
            self.logger.exception('[Back]: Error processing message on Back module:')
            
    def on_close(self):
        self.logger.debug("Admin Closed Connection")        
        admins.remove(self)

class ServerLayer():
    def __init__(self,proxy):
        global proxyref
        logging.debug("Starting ServerLayer")
        proxyref = proxy
        proxyref.send_message_to_server = self.send_message
        proxyref.broadcast_admins = self.broadcast_admins
        
    def send_message(self,message):
        global server_cycle
        global servers
        
        if len(servers) > 0:
            server_cycle.next().write_message(message)
        
    def broadcast_admins(self,message):
        for adm in admins:
            adm.write_message(message)
        