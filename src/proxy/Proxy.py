'''
Created on Oct 31, 2011

@author: Arthur Valadares

Proxy starts ProxyFront and ProxyBack
'''
import tornado.ioloop
import tornado.web
import logging
import logging.config
import front.Front as Front
import back.Back as Back
from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
client={}

# Intermediates messages between Front and Back
# TODO: Make it anonymous?
class Proxy():
    def send_message_to_server(self,message):
        #Back.ServerHandler.send_message(message)
        raise
    
    def send_message_to_client(self,message, clients):
        #Front.ClientHandler.send_message(message, clients)
        raise
        
    def test(self):
        logging.debug("Testing")
        
if __name__ == "__main__":
    # Clients and servers connect to the Proxy through different URLs
    lformat = '%(asctime)s | %(levelname)s [%(filename)s]: %(message)s'
    #logging.basicConfig(filename='proxy.log', level=logging.INFO, format=lformat)
    logging.config.fileConfig("logging.conf")
    
    proxy = Proxy()
    logging.debug("Starting ClientLayer")
    x = Front.ClientLayer(proxy)
    logging.debug("Starting ServerLayer")
    y = Back.ServerLayer(proxy)
    logging.debug("Proxy Started")

    
    application = tornado.web.Application([
    (r"/", Front.HTTPHandler),
    (r"/client", Front.ClientHandler),
    (r"/server", Back.ServerHandler),
    ])
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

