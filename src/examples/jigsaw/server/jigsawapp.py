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
import uuid
from random import randint
import time
from threading import Timer

global db
global pc
global settings
global datacon

settings = {}
db = None
pc = None
datacon = None
tables = {}
location = {}

img_url = ''
board = {}
grid = {}

# default frustum; w and h are determined by each client's canvas size
dfrus = {'x': 0,
         'y':0,
         'scale':1,
         'w': None,
         'h': None
         }

pieces = {}

clients = {}


class JigsawServerHandler(websocket.WebSocketHandler):
    def open(self):
        logging.debug("Jigsaw App Websocket Open")

        datacon.db.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        datacon.db.execute("delete from jigsaw")
        tables['game'] = datacon.db.retrieve_table_meta("jigsaw", "pid")
        Timer(5.0, datacon.db.__dump_to_database__).start()
        location['game'] = {}
        
        # DEBUG: Delete table at every start. Remove for deployment!

    def on_message(self, message):
        try:
            enc = json.loads(message)
    
            # send the config when the user joins
            if "NU" in enc:
                # get the user id
                userid = enc["NU"]
    
                pieces = {}
                dbresult = datacon.db.execute("select * from jigsaw")
                for item in dbresult:
                    pieces[item["pid"]] = item
                    
                
                # send the board config
                cfg = {'imgurl':img_url,
                       'board': board,
                       'grid': grid,
                       'frus': dfrus,
                       'pieces': pieces,
                       'myid': userid
                       }
                response = {'M': {'c': cfg}, 'U': userid}
                self.write_message(json.dumps(response))
    
            else:
                # usual message
                logging.debug(enc["M"])
                m = json.loads(enc["M"])
                userid = enc["U"][0]
    
                if 'rp' in m: # frustum update
                    #self.frus = m['rp']['v']
                    pass # TODO: update frustum table
                    # TODO: send pieces located in the new frustum
    
                elif 'pm' in m: # piece movement
                    pid = m['pm']['id']
                    piece = datacon.db.select('jigsaw', pid)[0]
                    lockid = piece['l']
                    if not lockid: # lock the piece if nobody owns it
                        datacon.db.update('jigsaw', [('l', userid)], pid)
                        logging.debug('%s starts dragging piece %s' % (userid, pid))
                    if lockid == userid: # change location if I'm the owner
                        # update piece coords
                        x = m['pm']['x']
                        datacon.db.update('jigsaw', [('x', x)], pid)
                        y = m['pm']['y']
                        datacon.db.update('jigsaw', [('y', y)], pid)
                        # add lock owner to msg to broadcast
                        response = {'M': {'pm': {'id': pid, 'x':x, 'y':y, 'l':lockid}}} #  no 'U' = broadcast
                        # broadcast
                        self.write_message(json.dumps(response))
    
                elif 'pd' in m: # piece drop
                    pid = m['pd']['id']
                    piece = datacon.db.select('jigsaw', pid)[0]
                    lockid = piece['l']
                    if lockid and lockid == userid: # I was the owner
                        # unlock piece
                        datacon.db.update('jigsaw', [('l', 0)], pid)
                        # update piece coords
                        x = m['pd']['x']
                        datacon.db.update('jigsaw', [('x', x)], pid)
                        y = m['pd']['y']
                        datacon.db.update('jigsaw', [('y', y)], pid)
    
                        # eventually bind piece 
                        bound = m['pd']['b']
                        if bound:
                            logging.debug('%s bound piece %s at %d,%d'
                                      % (userid, pid, x, y))
                            datacon.db.update('jigsaw', [('b', 1)], pid)
                        else:
                            logging.debug('%s dropped piece %s at %d,%d'
                                      % (userid, pid, x, y))
                        # add lock owner to msg to broadcast
                        response = {'M': {'pd': {'id': pid, 'x':x, 'y':y, 'b':bound, 'l':None}}} #  no 'U' = broadcast
                        self.write_message(json.dumps(response))
        except Exception, err:
            logging.exception("[jigsawapp]: Exception in message handling from client:")

    def on_close(self):
        logging.debug("App WebSocket closed")

handlers = [
    (r"/", JigsawServerHandler)
]

class JigsawServer():
    def __init__(self, settings):
        # Hook to the proxy connector admin messages. Needed to request data about other data servers
        pc.admin_hook = self.admin_parser
        if settings["main"]["start"] == "true":
            self.start_game()

    # Parses messages coming through admin channel of proxy
    def admin_parser(self, msg):
        if "BC" in msg:
            if "NEW" in msg["BC"]:
                global board
                global img_url
                global grid
                
                newgame_settings = msg["BC"]["NEW"]
                board = newgame_settings["board"]
                img_url = newgame_settings["main"]["img_url"]
                grid = newgame_settings["grid"]
                datacon.mapper.join(newgame_settings)

    def start_game(self):
        global board
        global img_url
        global grid
        
        board = settings["board"]
        img_url = settings["main"]["img_url"]
        grid = settings["grid"]                
        
        # Prepares the pieces in the database
        for r in range(grid['nrows']):
            for  c in range(grid['ncols']):
                pid = str(uuid.uuid4()) # piece id
                b = 0 # bound == correctly placed, can't be moved anymore
                l = 0# lock = id of the player moving the piece
                x = randint(0, board['w'] / 2)
                y = randint(0, board['h'] / 2)
                # Remove h later on!
                values = [pid, b, x, y, c, r, l]
                
                datacon.db.insert('jigsaw', values, pid)

        # Tells all other servers to start game and gives a fixed list of admins so that they all create the same Data Structure
        mod_settings = deepcopy(settings)
        del mod_settings["main"]["start"]
        mod_settings["ADMS"] = list(pc.admins)
        newmsg = {"BC":{"NEW":mod_settings}}
        json_message = json.dumps(newmsg)
        proxy_admin = random.choice(pc.admin_proxy.keys())
        proxy_admin.send(json_message)

# Parses settings for Jigsaw server. Extends helper input parser
def jigsaw_parser(config):
    app_config = {"main":{"start":"false"}}
    
    if config:
        try:
            set_main = {}
            set_board = {}
            set_grid = {}
            for k,v in config.items('Jigsaw_Main'):
                set_main[k] = v
            for k,v in config.items('Jigsaw_Board'):
                set_board[k] = float(v)
            for k,v in config.items('Jigsaw_Grid'):
                set_grid[k] = int(v)
            app_config["main"] = set_main
            app_config["board"] = set_board
            app_config["grid"] = set_grid
        except ConfigParser.NoSectionError:
            logging.warn("[jigsawpp]: No Section exception. Might be OK!")
    return app_config

if __name__ == "__main__":
    config = helper.parse_input('jigsawapp.cfg', jigsaw_parser)
    settings = config["app"]
    
    datacon = DataConn.DataConnector("JigsawSpacePart",config["ip"]+":"+config["port"])
    datacon.db = MySQLConnector(datacon)   
    datacon.mapper = SpacePartitioning(datacon)
    datacon.obm = ObjectManager(datacon, handlers)
    
    application = tornado.web.Application(handlers)
    application.listen(config["port"])

    logging.config.fileConfig("connector_logging.conf")
    logging.debug('[jigsawapp]: Starting jigsaw app in ' + config["ip"] + config["port"])
    t = Thread(target=tornado.ioloop.IOLoop.instance().start)
    t.daemon = True
    t.start()
    pc = ProxyConnector(config["proxies"],
                        "ws://" + config["ip"] + ':' + config["port"]) # server
    time.sleep(3)
    jigsaw = JigsawServer(settings)
    helper.terminal()
