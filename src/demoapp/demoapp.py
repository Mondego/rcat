from tornado import websocket
import tornado.ioloop
import tornado.web
from threading import Thread
from appconnector.proxyconn import ProxyConnector
import logging.config
import json
import data.mysqlconn as MySQLConn

pc = None
datacon = None

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        global datacon
        logging.debug("App Websocket Open")
        datacon = MySQLConn.MySQLConnector()
        datacon.open_connections('localhost', 'rcat', 'isnotamused', 'rcat')
        result = datacon.execute('SHOW TABLES')
        datacon.create_table("users","name")
        datacon.execute("delete from users")
        print result

    def on_message(self, message):
        msg = json.loads(message)
        newmsg = {}
        logging.debug(msg["M"])
        # Append metadata here. For now just sending the user and the message.
        newmsg["M"] = msg["M"].swapcase()
        newmsg["U"] = msg["U"]
        json_msg = json.dumps(newmsg)
        datacon.insert("users", [int(newmsg["M"]),0,1,2,3], newmsg["M"])
        datacon.update("users", [("top",3)], newmsg["M"])
        self.write_message(json_msg)

    def on_close(self):
        logging.debug("App WebSocket closed")
        
application = tornado.web.Application([
    (r"/", EchoWebSocket),
])

if __name__ == "__main__":
    application.listen(9999)
    logging.config.fileConfig("connector_logging.conf")
    t = Thread(target=tornado.ioloop.IOLoop.instance().start).start()
    pc = ProxyConnector(["ws://localhost:8888"],"ws://localhost:9999")
    
    
