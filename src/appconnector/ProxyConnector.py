import logging.config
import websocket
import time
from threading import Thread

class ProxyConnector():
    appWS = None
    proxyWS = None
    events = None
    manager = None

    def __init__(self,proxyURL,appURL):
        websocket.enableTrace(True)
        logging.config.fileConfig("connector_logging.conf")
        self.proxyWS = websocket.WebSocketApp(proxyURL,
                                    on_open = self.Proxy_on_open,
                                    on_message = self.Proxy_on_message,
                                    on_error = self.Proxy_on_error,
                                    on_close = self.Proxy_on_close)
        self.appWS = websocket.WebSocketApp(appURL,
                                    on_open = self.App_on_open,
                                    on_message = self.App_on_message,
                                    on_error = self.App_on_error,
                                    on_close = self.App_on_close)
        time.sleep(2)
        logging.debug("[ProxyConnector]: Connecting to AppServer in " + appURL)        
        t1 = Thread(target=self.appWS.run_forever).start()
        logging.debug("[ProxyConnector]: App Server Connected!")
        logging.debug("[ProxyConnector]: Connecting to Proxy in " + proxyURL)
        t2 = Thread(target=self.proxyWS.run_forever).start()
        logging.debug("[ProxyConnector]: Proxy Connected!")
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
    """
    TODO: Add ability for developers to start the connector "standalone". 
    Needs to read a conf file to know where AppServer and Proxy are
    """
    raise
