from tornado import websocket
import tornado.ioloop
import tornado.web
from threading import Thread
from appconnector.proxyconn import ProxyConnector
import logging.config
import json
import data.mysqlconn as MySQLConn
import ConfigParser, os

pc = None
datacon = None

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        global datacon
        logging.debug("App Websocket Open")
        datacon = MySQLConn.MySQLConnector("demoapp.cfg")
        datacon.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        result = datacon.execute('SHOW TABLES')
        datacon.create_table("chat","rid")
        datacon.execute("delete from chat")
        print result

    def on_message(self, message):
        enc = json.loads(message)
        logging.debug(enc["M"])
        
        msg = json.loads(enc["M"])
        user = enc["U"]
        
        newmsg = {}
        if "H" in msg: # Request history from..?
            if "ID" in msg["H"]:
                history = datacon.select("chat", msg["H"]["ID"])
                newmsg["M"] = str(history)
                newmsg["U"] = user
            else:
                logging.error("[demoapp]: No USERID passed.")
        elif "C" in msg: # Chat
            newmsg["M"] = msg["C"]["M"]
            insert_values = [msg["C"]["ID"],msg["C"]["M"]]
            datacon.insert("chat",insert_values,msg["C"]["ID"])
        json_msg = json.dumps(newmsg)
        self.write_message(json_msg)
        
        # Append metadata here. For now just sending the user and the message.
        """
        newmsg["M"] = msg["M"].swapcase()
        newmsg["U"] = msg["U"]
        json_msg = json.dumps(newmsg)
        datacon.insert("users", [int(newmsg["M"]),0,1,2,3], newmsg["M"])
        datacon.update("users", [("top",3)], newmsg["M"])
        
        """

    def on_close(self):
        logging.debug("App WebSocket closed")
        
application = tornado.web.Application([
    (r"/", EchoWebSocket),
    (r"/obm", MySQLConn.ObjectManager)
])

if __name__ == "__main__":
    application.listen(9999)
    logging.config.fileConfig("connector_logging.conf")    
    t = Thread(target=tornado.ioloop.IOLoop.instance().start).start()
    pc = ProxyConnector(["ws://localhost:8888"],"ws://localhost:9999")
    
    
