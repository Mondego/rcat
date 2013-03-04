from tornado import websocket
import socket
import tornado.ioloop
import tornado.web
import uuid

clients = {}

class EchoWebSocket(websocket.WebSocketHandler):
    """ Broadcast the messages sent by each client to all connected clients. """


    def open(self):
        """ Client joins -> add him to the broadcast list. """
        self.client_id = uuid.uuid4()
        clients[self.client_id] = self
        # ugly hack to disable Nagle in tornado
        self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print "WebSocket opened"


    def on_message(self, message):
        """ When my client sends a message, broadcast it to everyone """
        #handler = random.choice(clients.values())
        for handler in clients.values():
            handler.send_msg(message)
        #self.send_msg(message)


    def send_msg(self, message):
        """ Send a message to my client """
        try:
            self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
            self.write_message(message)
        except:
            print "Client disconnected before I could send."


    def on_close(self):
        try:
            del clients[self.client_id]
        except KeyError:
            print 'error: could not remove client from list of handlers'
        print "WebSocket closed"


application = tornado.web.Application([
    (r"/", EchoWebSocket),
])

if __name__ == "__main__":
    application.listen(8889)
    tornado.ioloop.IOLoop.instance().start()
