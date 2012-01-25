'''
Created on Oct 31, 2011

@author: Arthur Valadares

Proxy starts ProxyFront and ProxyBack
'''
import tornado.ioloop
import tornado.web
import tornado.websocket
import logging
from front import Front
from back import Back
from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
client={}

if __name__ == "__main__":
    # Clients and servers connect to the Proxy through different URLs
    application = tornado.web.Application([
    (r"/", Front.Handler),
    (r"/client", Front.ClientHandler),
    (r"/server", Back.ServerHandler),
    ])
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

    lformat = '%(asctime)s | %(levelname)s [%(name)s]: %(message)s'
    logging.basicConfig(filename='proxy.log', level=logging.INFO, format=lformat)
    logging.info("Start FrontProxy")
    x = Front.ClientLayer()
    logging.info("Start BackProxy")
    logging.info("Proxy Started")
