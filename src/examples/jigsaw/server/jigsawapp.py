from tornado import websocket
import tornado.ioloop
import tornado.web
from threading import Thread
from appconnector.proxyconn import ProxyConnector
import logging.config
import json
import data.mysqlconn as MySQLConn
import common.helper as helper

pc = None
datacon = None
appip = None
appport = None

class JigsawServer(websocket.WebSocketHandler):
    def open(self):
        global datacon
        logging.debug("Jigsaw App Websocket Open")
        datacon = MySQLConn.MySQLConnector(appip,appport)
        datacon.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        #result = datacon.execute('SHOW TABLES')
        datacon.create_table("jigsaw","pid")
        datacon.execute("delete from jigsaw")

    def on_message(self, message):
        try:
            enc = json.loads(message)
            logging.debug(enc["M"])
            
            msg = json.loads(enc["M"])
            user = enc["U"]
            
            newmsg = {}
            """
            Protocol: 
            "P":  Stands for new position type of message. Is a dictionary with two values:
                "NP": The new position
                "ID": The game ID of the client
            "RP": Stands for request pieces. Contains:
                "V": View area to look for pieces
                "ID": The game ID of the client
            """
            if "P" in msg:
                if "ID" in msg["P"]:
                    newmsg["M"] = msg["P"]["NP"]
                    insert_values = [msg["P"]["ID"],msg["P"]["NP"]]
                    datacon.insert("jigsaw",insert_values,msg["P"]["ID"])
                else:
                    logging.error("[jigsaw]: No USERID passed.")
            elif "RP" in msg: # Request history from..?
                if "ID" in msg["RP"]:
                    # TODO: Implement method to determine what pieces to request from database.
                    #pieces = datacon.select("jigsaw", msg["RP"][""])
                    #newmsg["M"] = json.dumps(pieces)
                    pass
                else:
                    logging.error("[jigsaw]: No USERID passed.")
            json_msg = json.dumps(newmsg)
            self.write_message(json_msg)
        except Exception as e:
            logging.error(e)
            newmsg["M"] = "ERROR: " + str(e)
            if user:
                newmsg["U"] = user
            json_msg = json.dumps(newmsg)
            self.write_message(json_msg)
            return False 
        
    def on_close(self):
        logging.debug("App WebSocket closed")
        
application = tornado.web.Application([
    (r"/", JigsawServer),
    (r"/obm", MySQLConn.ObjectManager)
])

if __name__ == "__main__":
    appip,appport = helper.parse_input('demoapp.cfg')
    application.listen(appport)
    logging.config.fileConfig("connector_logging.conf")
    logging.debug('[jigsawapp]: Starting jigsaw app in ' + appip + appport)    
    t = Thread(target=tornado.ioloop.IOLoop.instance().start)
    t.daemon = True
    t.start()
    pc = ProxyConnector(["ws://opensim.ics.uci.edu:8888"],"ws://" + appip + ':' + appport)
    helper.terminal()
    