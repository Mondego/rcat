'''
Created on Oct 31, 2011

@author: Arthur Valadares

ProxyMain starts Front and Back modules, which talk to clients and servers respectively. 
The proxy acts as an intermediary of messages from front to back and vice-versa through
the redefining of functions. 
'''

from common.benchmark import ResourceMonitor
from common.message import PROXY_DISTRIBUTION
from tornado.options import define, options
import back
import cProfile
import front
import logging.config
import os
import proxy as proxymod
import sys
import tornado.ioloop
import tornado.web
import uuid

define("port", default=8888, help="run on the given port", type=int)
define("benchmark",default=True, help="turns on resource management for the proxy")

def start(benchmark=False):
    # Clients and servers connect to the Proxy through different URLs
    logging.config.fileConfig("proxy_logging.conf")    
    """ 
    TODO: As new options are available, parse them and standardize the options dictionary.
    Current options are:
    
    DISTRIBUTION: 
    Description: Defines how messages are distributed from proxy to app servers.
    Options: Round-robin or sticky (messages from a client always hit the same app server)
    """
    proxy = proxymod.Proxy()
    proxy_options = {}
    proxy_options["DISTRIBUTION"] = PROXY_DISTRIBUTION.STICKY

    logging.debug("[proxy]: Loading proxy, please wait..")
    
    proxy.front = front.ClientLayer(proxy, proxy_options)
    proxy.back = back.ServerLayer(proxy, proxy_options)
    proxy.port = options.port

    logging.info("[proxy]: Proxy Started!")
    
    static_path = os.path.join("..", os.path.join("bin", "static"))
    logging.info("[proxy]: static path is " + static_path)
    
    if benchmark:
        filename = "proxy_resmon_" + str(uuid.uuid4())[:8] + ".csv"
        resmon = ResourceMonitor(filename, 
                                 metrics=[('numUsers', proxy.front.get_num_users)])
        resmon.start()

    application = tornado.web.Application([
    (r"/", front.HTTPHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': static_path}),
    (r"/client", front.ClientHandler),
    (r"/server", back.ServerHandler),
    (r"/admin", back.AdminHandler)
    ])
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
if __name__ == "__main__":
    if "--benchmark" in sys.argv:
        start(True)
    else:
        start(False)
    # To run profiler, uncomment next line
    # cProfile.run('start()', 'proxy.bench')
