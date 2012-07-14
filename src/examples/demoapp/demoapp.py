from tornado import websocket
import tornado.ioloop
from threading import Thread
from appconnector.proxyconn import ProxyConnector
from rcat import RCAT
import logging.config
import json
import data.dataconn as DataConn
import common.helper as helper
from data.plugins.obm import ObjectManager
from data.mappers.chatmapper import ChatManager
from data.db.mysqlconn import MySQLConnector

global datacon

pc = None
obm = None
ip = None
port = None

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        logging.debug("App Websocket Open")
        datacon.db.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        datacon.mapper.create_table("chat","mid")
        if len(rcat.pc.admins) == 1:
            logging.debug("[demoapp]: First server up, resetting table..")
            datacon.db.execute("truncate chat")

    def on_message(self, message):
        try:
            enc = json.loads(message)
            if "M" in enc:
                msg = json.loads(enc["M"])
                user = enc["U"]
                
                newmsg = {}
                if "H" in msg: # Request history from..?
                    if "ID" in msg["H"]:
                        history = datacon.mapper.select_per_user(msg["H"]["ID"])
                        newmsg["M"] = str(history)
                        newmsg["U"] = user
                    else:
                        logging.error("[demoapp]: No USERID passed.")
                elif "C" in msg: # Chat
                    newmsg["M"] = msg["C"]["M"]
                    insert_values = [msg["C"]["ID"],msg["C"]["M"]]
                    datacon.mapper.insert(insert_values)
                json_msg = json.dumps(newmsg)
                self.write_message(json_msg)
        except Exception as e:
            logging.exception("[demoapp]: Exception when treating message")
            return False 
        
    def on_close(self):
        logging.debug("App WebSocket closed")
      
if __name__ == "__main__":
    global datacon
    logging.config.fileConfig("connector_logging.conf")
    rcat = RCAT(EchoWebSocket,MySQLConnector,ChatManager,ObjectManager)
    datacon = rcat.datacon
    helper.terminal()
    
