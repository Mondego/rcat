"""
ProxyConnector.py
Summary: Hooks the proxies with the developer's application. Abstracts locating 
clients in the proxies from the application level. Also provides an event interface
for application control, e.g. "disconnect user from the proxy."  
"""

from threading import Thread
import json
import logging
import sys
import time
import websocket
import uuid

logger = logging.getLogger()

class ProxyConnector():
    # admin_hook: Used for applications and data connectors to access proxies
    admin_hook = None
    app = None
    proxies = None
    admins = None
    events = None
    manager = None
    client_proxy = None
    client_admin = None
    admin_proxy = None
    adm_id = None

    def __init__(self,proxyURLs,appURL):
        websocket.enableTrace(False)
        self.admin_proxy = {}
        self.proxies = set()
        self.admins = set()
        self.adm_id = str(uuid.uuid4())
        self.broadcasted = False
        
        if not appURL.endswith("/"):
                appURL += "/"
        for proxy in proxyURLs:
            if not proxy.endswith("/"):
                proxy += "/"
            adminWS = websocket.WebSocketApp(proxy+"admin",
                                        on_open = self.Admin_on_open,
                                        on_message = self.Admin_on_message,
                                        on_error = self.Admin_on_error,
                                        on_close = self.Admin_on_close)
            proxyWS = websocket.WebSocketApp(proxy+"server",
                                        on_open = self.Proxy_on_open,
                                        on_message = self.Proxy_on_message,
                                        on_error = self.Proxy_on_error,
                                        on_close = self.Proxy_on_close)
            self.admin_proxy[adminWS] = proxyWS
            self.proxies.add(proxyWS)
            logger.debug("[ProxyConnector]: Connecting to Proxy in " + proxy)
            pws = Thread(target=proxyWS.run_forever)
            pws.daemon = True
            pws.start()
            logger.debug("[ProxyConnector]: Proxy Connected!")
            logger.debug("[ProxyConnector]: Connecting to Admin in " + proxy)
            aws = Thread(target=adminWS.run_forever)
            aws.daemon = True
            aws.start()
            logger.debug("[ProxyConnector]: Admin Connected!")
        
        self.app = websocket.WebSocketApp(appURL,
                                    on_open = self.App_on_open,
                                    on_message = self.App_on_message,
                                    on_error = self.App_on_error,
                                    on_close = self.App_on_close)
        # TODO: Fix this sleep, looks so bad :(
        time.sleep(1)
        logger.debug("[ProxyConnector]: Connecting to AppServer in " + appURL)        
        t = Thread(target=self.app.run_forever)
        t.daemon = True
        t.start()
        logger.debug("[ProxyConnector]: App Server Connected!")
        
        self.manager = RMUVE_Manager()
        self.events = Event()
        self.client_proxy = {}
        self.client_admin = {}
    
    def set_admin_handler(self,admin_handler):
        self.admin_hook = admin_handler
        
    def move_user(self,user,newserver):
        msg = {"MU":{"NS":newserver,"U":user}}
        jsonmsg = json.dumps(msg)
        self.client_admin[user].send(jsonmsg)
        logger.debug("[proxyconn]: Moving user " + user + " to admin server id " + newserver)
        
    
    """
    Admin websocket events
    """
    
    def Admin_on_message(self,ws, message):
        try:
            logger.debug("Admin received message " + message)
            msg = json.loads(message)
            # New user
            if "NU" in msg:
                for user in msg["NU"]:
                    self.client_proxy[user] = self.admin_proxy[ws]
                    self.client_admin[user] = ws
                    self.app.send(message)
            # User disconnected
            elif "UD" in msg:
                if msg["UD"] in self.client_proxy:
                    del self.client_proxy[msg["UD"]]
                if msg["UD"] in self.client_admin:
                    
                    del self.client_admin[msg["UD"]]
                self.app.send(message)
            elif "NS" in msg:
                self.admins.update(set(msg["NS"]))
            elif "Failed" in msg:
                logger.error("[proxyconn]: Admin request failed! Request was " + str(msg["Failed"]))
            elif self.admin_hook:
                self.admin_hook(msg)
        except:
            logging.exception("[proxyconn]: Error receiving message through admin:")

    def Admin_on_error(self,ws, error):
        logger.exception("Exception in admin message channel: " + str(error))
    
    def Admin_on_close(self,ws):
        logger.debug("### Admin closed ###")
    
    def Admin_on_open(self,ws):
        logger.debug("### Admin opened ###")
        try:
            # Register Admin channel with the proxy
            msg = {}
            msg["REG"] = self.adm_id
            json_msg = json.dumps(msg)
            # Register admid with the Proxy's admin channel
            ws.send(json_msg)
            # Register admid with the Proxy message channel
            self.admin_proxy[ws].send(json_msg)
        except:
            logging.error("[proxyconn]: Error opening admin connection.")
    
    """
    App websocket events
    """
    
    def App_on_message(self,ws, message):
        logger.debug("App received message " + message)
        msg = json.loads(message)
        if "U" in msg:
            for client in msg["U"]:
                logger.debug("Sending message " + message + " to client " + client)
                try:
                    self.client_proxy[client].send(message)
                except:
                    logging.error("[proxyconn]: Failed to send message to user " + client + ". Maybe he's gone?")
        else:
            for proxy in self.proxies:
                try:
                    proxy.send(message)
                except:
                    logging.error("[proxyconn]: Failed to send message to proxy. Maybe it disconnected?")
   
    def App_on_error(self,ws, error):
        logger.debug(error)
    
    def App_on_close(self,ws):
        logger.debug("### App closed ###")
    
    def App_on_open(self,ws):
        logger.debug("### App open ###")
    
    """
    Proxy websocket events
    """    
    def Proxy_on_message(self,ws, message):
        """
        TODO: Assuming websocket only for now. The proxy should inform the type of data it received from the client in
        in the message
        """
        logging.debug("[proxyconn]: Message from proxy to app " + message)
        self.app.send(message)
    
    def Proxy_on_error(self,ws, error):
        logger.debug(error)
    
    def Proxy_on_close(self,ws):
        logger.debug("### closed ###")
    
    def Proxy_on_open(self,ws):
        logger.debug("### Proxy open ###")

"""
RMUVE_Manager: The app developer should substitute the event method to receive and send event notifications to RMUVE.
"""
class RMUVE_Manager():
    def recv_event(self, evt):
        raise Exception("Not yet implemented")

    def send_event(self,evt):
        if evt == Event.DISCONNECT:
            # TODO: Send disconnection event to proxy
            raise Exception("Not yet implemented")

"""
The Event class stores all standard events that between the system and the application. For instance, if the developer
wishes to disconnect a user (who is connected to the proxy), he can do connector.send_event(connector.event.Disconnect)
"""
class Event():
    DISCONNECT=0
    
if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print "Usage: python ProxyConnector.py <proxyurl1,proxyurl2,proxyurl3> <appurl>"
        exit()
    if (len(sys.argv) == 2):
        proxylist = []
    else:
        purls = sys.argv[1]
        proxylist = purls.split(',')
        
    appurl = sys.argv[len(sys.argv) - 1]
    pc = ProxyConnector(proxylist,appurl)
