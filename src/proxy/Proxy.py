'''
Created on Oct 31, 2011

@author: Arthur Valadares

Proxy starts ProxyFront and ProxyBack
'''
import tornado.ioloop
import tornado.web
import logging
import front.Front as Front
import back.Back as Back
from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
client={}

# Intermediates messages between Front and Back
# TODO: Make it anonymous?
class Proxy():
    def send_message_to_server(self,message):
        Back.ServerHandler.send_message(message)
    
    def send_message_to_client(self,message, clients):
        Front.ClientHandler.send_message(message, clients)
        
if __name__ == "__main__":
    # Clients and servers connect to the Proxy through different URLs
    lformat = '%(asctime)s | %(levelname)s [%(name)s]: %(message)s'
    logging.basicConfig(filename='proxy.log', level=logging.INFO, format=lformat)
    logging.info("Start FrontProxy")
    proxy = Proxy()
    print "Starting ClientLayer"
    x = Front.ClientLayer(proxy)
    logging.info("Start BackProxy")
    logging.info("Proxy Started")

    
    application = tornado.web.Application([
    (r"/", Front.Handler),
    (r"/client", Front.ClientHandler),
    (r"/server", Back.ServerHandler),
    ])
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


