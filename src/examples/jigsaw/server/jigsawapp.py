import random
from copy import deepcopy
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
import ConfigParser

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

class JigsawServerHandler(websocket.WebSocketHandler):
    def open(self):
        global datacon
        logging.debug("Jigsaw App Websocket Open")

        db.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        # TODO: "Game" should be the name of a particular game, set in options.
        tables['game'] = {}
        location['game'] = {}

        #result = datacon.execute('SHOW TABLES')
        #db.create_table("jigsaw", "pid")
        #db.execute("delete from jigsaw")

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
            newmsg = {}
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
    (r"/", JigsawServerHandler)
]

class JigsawServer():
    def __init__(self, settings):
        # Hook to the proxy connector admin messages. Needed to request data about other data servers
        pc.admin_hook = self.admin_parser

        if settings["start"] == "true":
            self.start_game()

    # Parses messages coming through admin channel of proxy
    def admin_parser(self, message):
        msg = json.loads(message)
        if "FW" in msg:
            if "NEW" in msg["FW"]:
                newgame_settings = msg["FW"]["NEW"]
                dm.join(newgame_settings)

    def start_game(self):
        # Space partitioning mapper creates the data structure for the puzzle and assigns space to servers
        # partitioning is a dictionary of server uuid to board partition, represented as two tuples, x0-x1, y0-y1
        partitioning = dm.create(settings, pc.admins)
        newmsg = {}
        newmsg["FW"] = {}
        json_message = ""
        mod_settings = deepcopy(settings)
        del mod_settings["start"]
        for adm in pc.admins:
            mod_settings["PART"] = partitioning[adm]
            newmsg["FW"]["ID"] = adm
            newmsg["FW"]["NEW"] = mod_settings
            json_message = json.dumps(newmsg)
            proxy_admin = random.choice(pc.admin_proxy.keys())
            proxy_admin.send(json_message)



# Parses settings for Jigsaw server. Extends helper input parser
def jigsaw_parser(config):
    global settings
    try:
        parsed = config.items('Jigsaw')
        settings = {}
        for k, v in parsed:
            settings[k] = v
    except ConfigParser.NoSectionError:
        settings = {}
        settings["start"] = "false"

if __name__ == "__main__":
    appip, appport, proxies = helper.parse_input('jigsawapp.cfg', jigsaw_parser)
    db = MySQLConnector(appip, appport) # TODO: should grab arguments from dataconn  
    dm = SpacePartitioning(db, 'first_puzzle')
    obm = ObjectManager(dm, handlers)
    datacon = DataConn.DataConnector("JigsawSpacePart", dm, db, obm)
    application = tornado.web.Application(handlers)
    application.listen(appport)

    logging.config.fileConfig("connector_logging.conf")
    logging.debug('[jigsawapp]: Starting jigsaw app in ' + appip + appport)
    t = Thread(target=tornado.ioloop.IOLoop.instance().start)
    t.daemon = True
    t.start()
    pc = ProxyConnector(proxies,
                        "ws://" + appip + ':' + appport) # server
    jigsaw = JigsawServer(settings)
    helper.terminal()
