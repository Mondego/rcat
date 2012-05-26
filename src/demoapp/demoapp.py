from tornado import websocket
import tornado.ioloop
from threading import Thread
from appconnector.proxyconn import ProxyConnector
import logging.config
import json
import data.dataconn as DataConn
import common.helper as helper
from data.plugins.obm import ObjectManager
from data.mappers.chatmapper import ChatManager
from data.db.mysqlconn import MySQLConnector

global db
global dm
global obm

pc = None
db = None
obm = None
dm = None
appip = None
appport = None

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        global dm
        logging.debug("App Websocket Open")
        db.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        result = db.execute('SHOW TABLES')
        dm.create_table("chat","rid")
        db.execute("delete from chat")
        print result

    def on_message(self, message):
        try:
            enc = json.loads(message)
            logging.debug(enc["M"])
            
            msg = json.loads(enc["M"])
            user = enc["U"]
            
            newmsg = {}
            if "H" in msg: # Request history from..?
                if "ID" in msg["H"]:
                    history = dm.select("chat", msg["H"]["ID"])
                    newmsg["M"] = str(history)
                    newmsg["U"] = user
                else:
                    logging.error("[demoapp]: No USERID passed.")
            elif "C" in msg: # Chat
                newmsg["M"] = msg["C"]["M"]
                insert_values = [msg["C"]["ID"],msg["C"]["M"]]
                dm.insert("chat",insert_values,msg["C"]["ID"])
            json_msg = json.dumps(newmsg)
            self.write_message(json_msg)
        except Exception as e:
            logging.error(e)
            newmsg["M"] = "ERROR"
            if user:
                newmsg["U"] = user
            json_msg = json.dumps(newmsg)
            self.write_message(json_msg)
            return False 
        
        
        # Append metadata here. For now just sending the user and the message.
        """
        newmsg["M"] = msg["M"].swapcase()
        newmsg["U"] = msg["U"]
        json_msg = json.dumps(newmsg)
        dm.insert("users", [int(newmsg["M"]),0,1,2,3], newmsg["M"])
        dm.update("users", [("top",3)], newmsg["M"])
        
        """

    def on_close(self):
        logging.debug("App WebSocket closed")
  

handlers = [
    (r"/", EchoWebSocket)
]
      
if __name__ == "__main__":
    appip,appport = helper.parse_input('demoapp.cfg')    
    logging.config.fileConfig("connector_logging.conf")
    logging.debug('[demoapp]: Starting app in ' + appip + ":" + appport)
    # TODO: Allow passing of options to determine which mapper and db to use. For now, hardcoded
    db = MySQLConnector(appip, appport)
    dm = ChatManager(db)
    obm = ObjectManager(dm,handlers)
    datacon = DataConn.DataConnector(dm, db, obm)

    application = tornado.web.Application(handlers)
    application.listen(appport)
    
    t = Thread(target=tornado.ioloop.IOLoop.instance().start)
    t.daemon = True
    t.start()
    pc = ProxyConnector(["ws://opensim.ics.uci.edu:8888"],"ws://" + appip + ':' + appport)
    helper.terminal()
    
