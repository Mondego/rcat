import logging
import websocket
import time
from threading import Thread
import json
import sys

logger = logging.getLogger()

class ProxyConnector():
    appWS = None
    proxies = None
    events = None
    manager = None
    client_location = None
    admin_proxy = None

    def __init__(self,proxyURLs,appURL):
        websocket.enableTrace(True)
        """
        TODO: Support more than one proxy! Right now only the last proxy in the list is used.
        """
        self.admin_proxy = {}
        self.proxies = []
        for proxy in proxyURLs:
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
            self.proxies.append(proxyWS)
            logger.debug("[ProxyConnector]: Connecting to Proxy in " + proxy)
            Thread(target=proxyWS.run_forever).start()
            logger.debug("[ProxyConnector]: Proxy Connected!")
            logger.debug("[ProxyConnector]: Connecting to Admin in " + proxy)
            Thread(target=adminWS.run_forever).start()
            logger.debug("[ProxyConnector]: Admin Connected!")
            
        self.appWS = websocket.WebSocketApp(appURL,
                                    on_open = self.App_on_open,
                                    on_message = self.App_on_message,
                                    on_error = self.App_on_error,
                                    on_close = self.App_on_close)
        time.sleep(1)
        logger.debug("[ProxyConnector]: Connecting to AppServer in " + appURL)        
        Thread(target=self.appWS.run_forever).start()
        logger.debug("[ProxyConnector]: App Server Connected!")
        
        self.manager = RMUVE_Manager()
        self.events = Event()
        self.client_location = {}
    
    """
    Admin websocket events
    """
    
    def Admin_on_message(self,ws, message):
        logger.debug("Admin received message " + message)
        msg = json.loads(message)
        if "NU" in msg:
            if msg["NU"] not in self.client_location:
                self.client_location[msg["NU"]] = self.admin_proxy[ws]
        elif "LU" in msg:
            for user in msg["LU"]:
                self.client_location[user] = self.admin_proxy[ws]
        elif "UD" in msg:
            if msg["UD"] in self.client_location:
                del self.client_location[msg["UD"]]
        logger.debug("List of users: " + str(self.client_location))
    
    def Admin_on_error(self,ws, error):
        print error
    
    def Admin_on_close(self,ws):
        print "### Admin closed ###"
    
    def Admin_on_open(self,ws):
        print "### Admin open ###"
    
    """
    App websocket events
    """
    
    def App_on_message(self,ws, message):
        logger.debug("App received message " + message)
        msg = json.loads(message)
        if "U" in msg:
            for client in msg["U"]:
                logger.debug("Sending message " + message + " to client " + client)
                self.client_location[client].send(message)
        else:
            for server in self.proxies:
                server.send(message)
   
    def App_on_error(self,ws, error):
        print error
    
    def App_on_close(self,ws):
        print "### closed ###"
    
    def App_on_open(self,ws):
        print "### App open ###"
    
    """
    Proxy websocket events
    """    
    def Proxy_on_message(self,ws, message):
        """
        TODO: Assuming websocket only for now. The proxy should inform the type of data it received from the client in
        in the message
        """
        self.appWS.send(message)
    
    def Proxy_on_error(self,ws, error):
        print error
    
    def Proxy_on_close(self,ws):
        print "### closed ###"
    
    def Proxy_on_open(self,ws):
        print "### Proxy open ###"

"""
RMUVE_Manager: The app developer should substitute the event method to receive and send event notifications to RMUVE.
"""
class RMUVE_Manager():
    def recv_event(self, evt):
        raise

    def send_event(self,evt):
        if evt == Event.DISCONNECT:
            # TODO: Send disconnection event to proxy
            raise

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
        if len(proxylist) > 1:
            print "WARNING! Only one proxy is supported in the current version. Using last proxy in the list."
        
    appurl = sys.argv[len(sys.argv) - 1]
    pc = ProxyConnector(proxylist,appurl)
