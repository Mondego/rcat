import tornado.ioloop
import tornado.web
import time

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")
        
    def post(self):
        timestamp = time.time()
        argument = self.get_argument("message", False)
        if (argument):
            self.write(argument + ";timestamp: " + str(timestamp))


application = tornado.web.Application([
    (r"/", MainHandler),
])

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    