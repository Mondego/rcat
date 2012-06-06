from tornado import websocket
import tornado.ioloop
import tornado.web
from threading import Thread
from appconnector.proxyconn import ProxyConnector
import logging.config
import json
import common.helper as helper
from data.plugins.obm import ObjectManager
from data.mappers.spacepart import SpacePartitioning 
from data.db.mysqlconn import MySQLConnector
import data.dataconn as DataConn

global db
global pc
global settings

settings = None
db = None
pc = None
datacon = None
appip = None
appport = None
tables = {}
location = {}

class JigsawServer(websocket.WebSocketHandler):
    def open(self):
        global datacon
        logging.debug("Jigsaw App Websocket Open")
        
        db.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        # TODO: "Game" should be the name of a particular game, set in options.
        tables['game'] = {}
        location['game'] = {}
        
        #result = datacon.execute('SHOW TABLES')
        db.create_table("jigsaw", "pid")
        db.execute("delete from jigsaw")

    def on_message(self, message):
        try:
            enc = json.loads(message)
            logging.debug(enc["M"])

            msg = json.loads(enc["M"])
            user = enc["U"]

            newmsg = {}
            """
            Protocol: 
            "P":  Piece movement message. Exchanged between server and clients.
                "x": The piece's new x
                "y": The piece's new y
                "id": the piece's uuid
            "RP": Frustum update message. From clients to server.
                "V": client's frustum
            "c": config of the puzzle, sent when client connects
                "imgurl": url of the puzzle image
                "board": stores w, h, maxScale, minScale
                "grid": stores x, y, ncols, nrows, cellw, cellh
                "pieces": mapping of pid to {pid, x, y, c, r}
            """
            if "P" in msg:
                if "ID" in msg["P"]:
                    newmsg["M"] = msg["P"]["NP"]
                    insert_values = [msg["P"]["ID"], msg["P"]["NP"]]
                    datacon.insert("jigsaw", insert_values, msg["P"]["ID"])
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

handlers = [
    (r"/", JigsawServer)
]

def jigsaw_parser(config):
    global settings
    parsed = config.items('Jigsaw')
    settings = {}
    for k,v in parsed:
        settings[k] = v

def start_game():
    newmsg = {}
    newmsg["BC"] = {}
    newmsg["M"] = settings
    json_message = json.dumps(newmsg)
    pc.appWS.write_message(json_message)

if __name__ == "__main__":
    appip, appport, proxies = helper.parse_input('jigsawapp.cfg',jigsaw_parser)
    db = MySQLConnector(appip, appport)
    dm = SpacePartitioning(db,'first_puzzle')
    obm = ObjectManager(dm,handlers)
    datacon = DataConn.DataConnector("JigsawSpacePart",dm, db, obm)
    application = tornado.web.Application(handlers)
    application.listen(appport)

    logging.config.fileConfig("connector_logging.conf")
    logging.debug('[jigsawapp]: Starting jigsaw app in ' + appip + appport)
    t = Thread(target=tornado.ioloop.IOLoop.instance().start)
    t.daemon = True
    t.start()
    pc = ProxyConnector(proxies, 
                        "ws://" + appip + ':' + appport) # server
    if settings['start'] == "true":
        start_game()
    helper.terminal()
