from tornado import websocket
import tornado.ioloop
import tornado.web
from threading import Thread
from appconnector.ProxyConnector import ProxyConnector
import time

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        print "App Websocket Open"

    def on_message(self, message):
        self.write_message(message)

    def on_close(self):
        print "App WebSocket closed"
        
application = tornado.web.Application([
    (r"/", EchoWebSocket),
])

if __name__ == "__main__":
    application.listen(9999)
    #tornado.ioloop.IOLoop.instance().start()
    t = Thread(target=tornado.ioloop.IOLoop.instance().start).start()
    pc = ProxyConnector("ws://localhost:8888/server","ws://localhost:9999/")
    
    
