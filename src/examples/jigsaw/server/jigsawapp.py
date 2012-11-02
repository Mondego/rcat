from copy import deepcopy
from data.db.mysqlconn import MySQLConnector
from data.mappers.spacepart import SpacePartitioning
from data.plugins.obm import ObjectManager
from random import randint
from rcat import RCAT
from threading import Thread
from tornado import websocket
from tornado.ioloop import IOLoop
from collections import defaultdict
import ConfigParser
import common.helper as helper
import json
import logging.config
import random
import threading
import time
import uuid

global db
global pc
global settings
global datacon

settings = {}
db = None
datacon = None
rcat = None
tables = {}
location = {}
pchandler = None
game_over = False

img_settings = {}
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

clientsConnected = 0

class JigsawServerHandler(websocket.WebSocketHandler):
    def open(self):
        global pchandler
        pchandler = self
        logging.debug("Jigsaw App Websocket Open")


    def on_message(self, message):
        JigsawRequestParser(self, message).start()

    def on_close(self):
        logging.debug("App WebSocket closed")

handlers = [
    (r"/", JigsawServerHandler)
]

class JigsawRequestParser(Thread):
    def __init__(self, handler, message):
        Thread.__init__(self)
        self.daemon = True
        self.handler = handler
        self.sched = IOLoop.instance().add_callback
        self.message = message
        self.evt = None

    def run(self):
        global clientsConnected
        # TODO: userid and userid[0] is confusing 
        try:
            enc = json.loads(self.message)

            # send the config when the user joins
            if "NU" in enc:
                if enc["SS"] != rcat.pc.adm_id:
                    clientsConnected += 1
                else:
                    # get the user id
                    new_user_list = enc["NU"]
                    if len(new_user_list) != 1:
                        raise Exception('Not supporting multiple new users')
                    new_user = new_user_list[0]

                    pieces = {}
                    pieces = datacon.mapper.select_all()
                    scores = datacon.mapper.get_user_scores()
                    datacon.mapper.create_user(new_user)
                    # send the board config
                    cfg = {'img':img_settings,
                           'board': board,
                           'grid': grid,
                           'frus': dfrus,
                           'pieces': pieces,
                           'myid': new_user,
                           'clients': clientsConnected,
                           'scores' : scores
                           }
                    response = {'M': {'c': cfg}, 'U': [new_user]}
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)
                    clientsConnected += 1
                    # Inform other clients of client connection
                    response = {'M': enc}
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)
            elif "UD" in enc:
                #User was disconnected. Inform other clients
                clientsConnected -= 1
                if enc["SS"] == rcat.pc.adm_id:
                    response = {'M': enc}
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)

            else:
                # usual message
                logging.debug(enc["M"])
                m = json.loads(enc["M"])
                userid = enc["U"][0]

                if 'rp' in m: # frustum update
                    pf = datacon.mapper.set_user_frustrum(userid, m['rp']['v'])
                    response = {'M': {'pf':pf}, 'U':[userid]}
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)

                    # TODO: send pieces located in the new frustum
                elif 'usr' in m:
                    update_res = datacon.mapper.new_user_connected(userid, m['usr'])
                    response = {'M': {'scu':update_res}}
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)

                elif 'pm' in m: # piece movement
                    pid = m['pm']['id']
                    x = m['pm']['x']
                    y = m['pm']['y']
                    piece = datacon.mapper.select(x, y, pid)

                    lockid = piece['l']
                    if not lockid or lockid == "None": # lock the piece if nobody owns it
                        lockid = userid
                        datacon.mapper.update(x, y, [('l', lockid)], pid)
                        logging.debug('%s starts dragging piece %s' % (userid, pid))
                    #TODO: Better detect conflict. Right now I privilege the latest attempt, not the first.
                    #if lockid == userid: # change location if I'm the owner
                    # update piece coords
                    loc = datacon.mapper.update(x, y, [('x', x), ('y', y)], pid)
                    if loc != "LOCAL":
                        rcat.pc.move_user(userid, loc)
                    # add lock owner to msg to broadcast
                    response = {'M': {'pm': {'id': pid, 'x':x, 'y':y, 'l':lockid}}} #  no 'U' = broadcast
                    # broadcast
                    jsonmsg = json.dumps(response)
                    # TODO: Only send updates to concerned users
                    self.handler.write_message(jsonmsg)
                    #else:
                    #    logging.debug("[jigsawapp]: Weird value for lockid: " + str(lockid))

                elif 'pd' in m: # piece drop
                    pid = m['pd']['id']
                    x = m['pd']['x']
                    y = m['pd']['y']

                    piece = datacon.mapper.select(x, y, pid)

                    if not 'l' in piece:
                        logging.warning("[jigsawapp]: Got something weird: " + str(piece))
                        return
                    lockid = piece['l']
                    if lockid and lockid == userid: # I was the owner
                        # unlock piece
                        datacon.mapper.update(x, y, [('l', None)], pid)
                        # update piece coords
                        datacon.mapper.update(x, y, [('x', x), ('y', y)], pid)

                        # eventually bind piece 
                        bound = m['pd']['b']
                        if bound:
                            logging.debug('%s bound piece %s at %d,%d'
                                      % (userid, pid, x, y))
                            datacon.mapper.update(x, y, [('b', 1)], pid)

                            # Update score board. Separate from 'pd' message because this is always broadcasted.
                            update_res = datacon.mapper.add_to_user_score(userid)
                            response = {'M': {'scu':update_res}}
                            jsonmsg = json.dumps(response)
                            self.handler.write_message(jsonmsg)

                        else:
                            logging.debug('%s dropped piece %s at %d,%d'
                                      % (userid, pid, x, y))
                        # add lock owner to msg to broadcast
                        response = {'M': {'pd': {'id': pid, 'x':x, 'y':y, 'b':bound, 'l':None}}} #  no 'U' = broadcast
                        jsonmsg = json.dumps(response)
                        self.handler.write_message(jsonmsg)
                # End game request from client
                elif 'go':
                    global game_over
                    # Am I already waiting for the game to end?
                    if not game_over:
                        game_over = True
                        # TODO: Send final game score
                        print "Game end request received"
                        res = datacon.mapper.check_game_end()
                        if res:
                            msg = {'M': {'go':True}}
                            jsonmsg = json.dumps(msg)
                            self.handler.write_message(jsonmsg)
                elif 'ng' in m:
                    pass

                elif 'rg' in m:
                    pass

        except Exception, err:
            logging.exception("[jigsawapp]: Exception in message handling from client:")



class JigsawServer():
    def __init__(self):
        global settings
        # Hooks up to get messages coming in admin channel. 
        # Used to know about new users, servers, and their disconnections.
        rcat.pc.set_admin_handler(self.admin_parser)
        config = helper.open_configuration('jigsaw.cfg')
        settings = self.jigsaw_parser(config)
        helper.close_configuration('jigsaw.cfg')

        user = settings["db"]["user"]
        password = settings["db"]["password"]
        address = settings["db"]["address"]
        database = settings["db"]["db"]

        datacon.db.open_connections(address, user, password, database)
        # DEBUG ONLY: Delete for deployment
        if len(rcat.pc.admins) == 1:
            datacon.mapper.create_table("jigsaw", "pid", True)
            logging.debug("[jigsawapp]: First server up, resetting table..")
            #datacon.db.execute("truncate jigsaw")
        else:
            datacon.mapper.create_table("jigsaw", "pid")

        if settings["main"]["start"] == "true":
            self.start_game()

    def jigsaw_parser(self, config):
        app_config = {"main":{"start":"false"}}

        if config:
            try:
                set_main = {}
                set_board = {}
                set_img = {}
                set_grid = {}
                set_db = {}
                for k, v in config.items('Jigsaw_Main'):
                    set_main[k] = v
                app_config["main"] = set_main
                for k, v in config.items('Jigsaw_DB'):
                    set_db[k] = v
                app_config["db"] = set_db
                for k, v in config.items('Jigsaw_Image'):
                    set_img[k] = v
                app_config["img"] = set_img
                for k, v in config.items('Jigsaw_Board'):
                    set_board[k] = float(v)
                app_config["board"] = set_board
                for k, v in config.items('Jigsaw_Grid'):
                    set_grid[k] = int(v)
                app_config["grid"] = set_grid

            except ConfigParser.NoSectionError:
                logging.warn("[jigsawpp]: No Section exception. Might be OK!")
        return app_config

    # Parses messages coming through admin channel of proxy
    def admin_parser(self, msg):
        if "BC" in msg:
            if "NEW" in msg["BC"]:
                global board
                global img_settings
                global grid

                newgame_settings = msg["BC"]["NEW"]
                board = newgame_settings["board"]
                img_settings = newgame_settings["img"]
                grid = newgame_settings["grid"]
                datacon.mapper.join(newgame_settings)
                if settings["main"]["start"] == "true":
                    logging.info("[jigsawapp]: Starting game, please wait...")
                    count = datacon.db.count("jigsaw")
                    #TODO: Add condition where new game is being started
                    if count > 0:
                        logging.info("[jigsawapp]: Recovering last game.")
                        datacon.mapper.recover_last_game()
                    else:
                        # Prepares the pieces in the database
                        for r in range(grid['nrows']):
                            for  c in range(grid['ncols']):
                                pid = str(uuid.uuid4()) # piece id
                                b = 0 # bound == correctly placed, can't be moved anymore
                                l = None# lock = id of the player moving the piece
                                x = randint(0, board['w'] - grid['cellw'])
                                y = randint(0, board['h'] - grid['cellh'])
                                # Remove h later on!
                                values = [pid, b, x, y, c, r, l]

                                datacon.mapper.insert(values, pid)

                    logging.info("[jigsawapp]: Game has loaded. Have fun!")

    def start_game(self):
        """
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
                
                datacon.mapper.insert(values, pid)
        """

        # Tells all other servers to start game and gives a fixed list of admins so that they all create the same Data Structure
        mod_settings = deepcopy(settings)
        del mod_settings["main"]["start"]
        mod_settings["ADMS"] = list(rcat.pc.admins)
        newmsg = {"BC":{"NEW":mod_settings}}
        json_message = json.dumps(newmsg)
        proxy_admin = random.choice(rcat.pc.admin_proxy.keys())
        proxy_admin.send(json_message)


if __name__ == "__main__":
    logging.config.fileConfig("connector_logging.conf")
    rcat = RCAT(JigsawServerHandler, MySQLConnector, SpacePartitioning, ObjectManager)
    datacon = rcat.datacon
    logging.debug('[jigsawapp]: Starting jigsaw..')

    time.sleep(2)

    jigsaw = JigsawServer()
    helper.terminal()
