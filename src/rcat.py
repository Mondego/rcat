'''
Created on Jul 11, 2012

@author: arthur
'''

from appconnector.proxyconn import ProxyConnector
from common.benchmark import ResourceMonitor
from data.dataconn import DataConnector
from data.plugins.obm import OBMHandler
from threading import Thread
import common.helper as helper
import logging
import tornado.web
import uuid

class RCAT():
    application = None
    pc = None
    datacon = None
    resmon = None
    def __init__(self,handler,db=None,mapper=None,obm=None):
        handlers = []
        handlers.append((r"/", handler))
        rcat_config = helper.parse_input('rcat.cfg')
        ip = rcat_config["ip"]
        port = rcat_config["port"]
        proxies = rcat_config["proxies"]
        plugins = rcat_config["plugins"]
        if "benchmark" in plugins:
            filename = "rcat_resmon_" + str(uuid.uuid4())[:8] + ".csv"
            self.resmon = ResourceMonitor(filename)
            self.resmon.start()
        if obm:
            handlers.append((r"/obm", OBMHandler))
        
        logging.debug('[rcat]: Starting app in ' + ip + ":" + port)
        
        application = tornado.web.Application(handlers)
        application.listen(port)
        
        t = Thread(target=tornado.ioloop.IOLoop.instance().start)
        t.daemon = True
        t.start()
        
        self.pc = ProxyConnector(proxies, "ws://" + ip + ':' + port) # app server
        self.datacon = DataConnector("RCAT",self.pc.adm_id)
        self.datacon.host = ip+":"+port
        if db:
            if "persist_timer" in rcat_config and rcat_config["persist_timer"]:
                self.datacon.db = db(self.datacon,rcat_config["persist_timer"])
            else:
                self.datacon.db = db(self.datacon)
            
        if mapper:
            self.datacon.mapper = mapper(self.datacon)
        if obm:
            self.datacon.obm = obm(self.datacon)