'''
Created on Oct 31, 2011

@author: Arthur Valadares

Proxy starts Front and Back modules, which talk to clients and servers respectively. 
The proxy acts as an intermediary of messages from front to back and vice-versa through
the redefining of functions. 
'''
import tornado.ioloop
import tornado.web
import logging.config
import front.Front as Front
import back.Back as Back
from tornado.options import define, options
from common.message import PROXY_DISTRIBUTION

define("port", default=8888, help="run on the given port", type=int)
client={}

# Intermediates messages between Front and Back
class Proxy():
    def send_message_to_server(self,message,server=None):
        raise Exception('[Proxy]: Not implemented!')
    
    def broadcast_admins(self,message):
        raise Exception('[Proxy]: Not implemented!')
    
    def send_message_to_client(self,message, clients):
        raise Exception('[Proxy]: Not implemented!')
    
    def authorize_client(self, authclient, cuuid):
        raise Exception('[Proxy]: Not implemented!')
    
    def list_users(self):
        raise Exception('[Proxy]: Not implemented!')
    
    def sticky_server(self):
        raise Exception('[Proxy]: Not implemented!')
    
    def test(self):
        logging.debug("Testing")
        
if __name__ == "__main__":
    # Clients and servers connect to the Proxy through different URLs
    logging.config.fileConfig("logging.conf")    
    """ 
    TODO: As new options are available, parse them and standardize the options dictionary.
    Current options are:
    
    DISTRIBUTION: 
    Description: Defines how messages are distributed from proxy to app servers.
    Options: Round-robin or sticky (messages from a client always hit the same app server)
    """
    proxy = Proxy()
    proxy_options = {}
    proxy_options["DISTRIBUTION"] = PROXY_DISTRIBUTION.STICKY
    
    logging.debug("Starting ClientLayer")
    x = Front.ClientLayer(proxy, proxy_options)
    logging.debug("Starting ServerLayer")
    y = Back.ServerLayer(proxy, proxy_options)
    logging.debug("Proxy Started")

    
    application = tornado.web.Application([
    (r"/", Front.HTTPHandler),
    (r"/client", Front.ClientHandler),
    (r"/server", Back.ServerHandler),
    (r"/admin", Back.AdminHandler),
    ])
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


