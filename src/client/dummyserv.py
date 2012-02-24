import tornado.ioloop
import tornado.web
import tornado.websocket

class WSHandler(tornado.websocket.WebSocketHandler):
    
    def open(self):
        print 'new connection '
        self.write_message("Hello from serv")
      
    def on_message(self, message):
        print 'message received %s' % message

    def on_close(self):
        print 'connection closed'
      



class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello http")

app = tornado.web.Application([
    (r"/", MainHandler),
    (r'/ws', WSHandler)
])


if __name__ == "__main__":
    app.listen(9000)
    print 'server listens on 9000'
    #http_server = tornado.httpserver.HTTPServer(app_http)
    #http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
