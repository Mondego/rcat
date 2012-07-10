'''
Created on Oct 31, 2011

@author: Arthur Valadares

ProxyMain starts Front and Back modules, which talk to clients and servers respectively. 
The proxy acts as an intermediary of messages from front to back and vice-versa through
the redefining of functions. 
'''

import tornado.ioloop
import tornado.web
import logging.config
import proxy
import front
import back
from tornado.options import define, options
from common.message import PROXY_DISTRIBUTION

define("port", default=8888, help="run on the given port", type=int)

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
    proxy = proxy.Proxy()
    proxy_options = {}
    proxy_options["DISTRIBUTION"] = PROXY_DISTRIBUTION.STICKY

    logging.debug("Proxy Starting")
    
    proxy.front = front.ClientLayer(proxy, proxy_options)
    proxy.back = back.ServerLayer(proxy, proxy_options)

    logging.debug("Proxy Started")
    
    application = tornado.web.Application([
    (r"/", front.HTTPHandler),
    (r"/client", front.ClientHandler),
    (r"/server", back.ServerHandler),
    (r"/admin", back.AdminHandler),
    ])
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()