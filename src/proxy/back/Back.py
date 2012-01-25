import json
import tornado.web
import tornado.websocket
from proxy.front.Front import ClientHandler
from common.message import MESSAGE_TYPE

servers = []

class ServerHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print "WebSocket opened"
        servers.append(self)
        
    def on_message(self, message):
        try:
            msg = json.loads(message)
            if msg["type"] == MESSAGE_TYPE.ACCEPTED:
                print "Client authentication accepted."
                
            
        except Exception as inst:
            self.write_message("Not valid JSON")
            print inst

    def on_close(self):
        print "WebSocket closed"
        
    def send_message(self,message):
        if len(servers) > 0:
            servers.pop().write_message(message)
