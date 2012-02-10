from tornado import websocket
import tornado.ioloop
import tornado.web
from threading import Thread
from appconnector.ProxyConnector import ProxyConnector
import logging.config
import json

pc = None

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        print "App Websocket Open"

    def on_message(self, message):
        msg = json.loads(message)
        newmsg = {}
        print msg["M"]
        # Append metadata here. For now just sending the user and the message.
        newmsg["M"] = msg["M"].swapcase()
        newmsg["U"] = msg["U"]
        json_msg = json.dumps(newmsg)
        self.write_message(json_msg)

    def on_close(self):
        print "App WebSocket closed"
        
application = tornado.web.Application([
    (r"/", EchoWebSocket),
])

if __name__ == "__main__":
    application.listen(9999)
    #tornado.ioloop.IOLoop.instance().start()
    logging.config.fileConfig("connector_logging.conf")
    t = Thread(target=tornado.ioloop.IOLoop.instance().start).start()
    pc = ProxyConnector(["ws://localhost:8888/"],"ws://localhost:9999/")
    
    
