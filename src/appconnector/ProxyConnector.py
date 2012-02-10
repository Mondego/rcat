import logging
import websocket
import time
from threading import Thread
import sys

logger = logging.getLogger()

class ProxyConnector():
    appWS = None
    proxyWS = None
    events = None
    manager = None

    def __init__(self,proxyURLs,appURL):
        websocket.enableTrace(True)
        """
        TODO: Support more than one proxy! Right now only the last proxy in the list is used.
        """
        for proxy in proxyURLs:
            self.proxyWS = websocket.WebSocketApp(proxy,
                                        on_open = self.Proxy_on_open,
                                        on_message = self.Proxy_on_message,
                                        on_error = self.Proxy_on_error,
                                        on_close = self.Proxy_on_close)
            logger.debug("[ProxyConnector]: Connecting to Proxy in " + proxy)
            Thread(target=self.proxyWS.run_forever).start()
            logger.debug("[ProxyConnector]: Proxy Connected!")
            
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
    
    """
    App websocket events
    """
    
    def App_on_message(self,ws, message):
        self.proxyWS.send(message)
    
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
