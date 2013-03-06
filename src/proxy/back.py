"""
Back.py
Summary: Opens a websocket listener for clients. Messages sent to Back are forwarded 
to Front through Proxy, in order to reach the server. 
Messages from server are received in Front, and passed to Back so they can be delivered to client.
"""
import itertools
import json
import logging
import proxy
import socket
import tornado.websocket

servers = []
admins = {}
sticky_client = {}
server_cycle = None
server_admid = {}
proxyref = None
admin_proxy = {}
logger = logging.getLogger("proxy")
DISABLE_NAGLE = 1

class ServerHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        global servers
        global server_cycle

        # set TCP_NODELAY to 1 to disable Nagle
        self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, DISABLE_NAGLE)

        logger.info("### New server connected")
        servers.append(self)
        server_cycle = itertools.cycle(servers)

    def on_message(self, message):
        try:
            msg = json.loads(message)
            logger.debug(message)
            if "U" in msg:
                users = msg["U"]
                logger.debug("Sending message " + str(msg["M"]) + " to users " + str(users))
                proxyref.front.send_message_to_client(msg["M"], users)
            # App connector is registering its admid with this connection
            elif "REG" in msg:
                admid = msg["REG"]
                server_admid[self] = admid
                admin_proxy[admid] = self
            else:
                proxyref.front.send_message_to_client(msg["M"])
        except Exception:
            logger.exception('[Back]: Error processing message on Back module:')

    def on_close(self):
        global servers
        global server_cycle

        logger.info("### Server disconnected")
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
            logger.debug("[back]: Got admin message: " + str(msg))
            newmsg = {}

            # Internal requests
            ### List of Users - Request
            if "LUR" in msg:
                newmsg["NU"] = proxyref.front.list_users()
                json_newmsg = json.dumps(newmsg)
                self.write_message(json_newmsg)
            # Request list of servers
            elif "LSR" in msg:
                newmsg["NS"] = admins.keys()
                json_newmsg = json.dumps(newmsg)
                print json_newmsg
                self.write_message(json_newmsg)
            # Admin handler registers its UUID 
            elif "REG" in msg:
                self.admid = msg["REG"]
                admins[self.admid] = self
                newmsg = {"NS":admins.keys()}
                jsonmsg = json.dumps(newmsg)
                for adm in admins.values():
                    adm.write_message(jsonmsg)
            # App Server requesting to move user
            elif "MU" in msg:
                ns = msg["MU"]["NS"]
                user = str(msg["MU"]["U"])
                newserver = admin_proxy[ns]
                res = proxyref.front.move_client(user,newserver)
                if not res:
                    newmsg = {"Failed":msg}
                    jsonmsg = json.dumps(newmsg) 
                    self.write_message(jsonmsg)

            # Developer customized messages
            ### Broadcast messages to all admins
            elif "BC" in msg:
                proxyref.back.broadcast_admins(msg)
            # Forward message to specific server
            elif "FW" in msg:
                logger.debug("[back]: Got admin FW message: " + str(msg))
                aid = msg["FW"]["ID"]
                msg["FW"]["ID"] = self.admid
                json_newmsg = json.dumps(msg)
                admins[aid].write_message(json_newmsg)

        except Exception:
            logger.exception('[Back]: Error processing message on Back module:')

    def on_close(self):
        try:
            logger.debug("Admin Closed Connection")
            del admins[self.admid]
            del server_admid[self]
        except Exception:
            logger.warning("[back]: Problem deleting admin from dictionary. Maybe it's already gone?")

class ServerLayer(proxy.AbstractBack):
    def __init__(self, proxy, options):
        global proxyref
        global serverlayer
        serverlayer = self
        logging.debug("Starting ServerLayer")
        proxyref = proxy

    def get_admid(self, server):
        if server in server_admid:
            return server_admid[server]
        else:
            logging.error("[back]: Sync error, couldn't find id for this server.")

    def send_message_to_server(self, message, server=None):
        if (server):
            server.write_message(message)
        elif len(servers) > 0:
            server_cycle.next().write_message(message)

    def sticky_server(self):
        return server_cycle.next()

    def broadcast_admins(self, message):
        for adm in admins.values():
            adm.write_message(message)
