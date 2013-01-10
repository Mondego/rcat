from collections import defaultdict
from copy import deepcopy
from data.db.sqlalchemyconn import SQLAlchemyConnector
from data.plugins.obm import ObjectManager
from examples.jigsaw.server.mapper.dbobjects import Piece, User
from examples.jigsaw.server.mapper.mapper import JigsawMapper
from random import randint
from rcat import RCAT
from threading import Thread
from tornado import websocket
from tornado.ioloop import IOLoop
import ConfigParser
import common.helper as helper
import json
import logging.config
import random
import time
import uuid

global db
global pc
global settings
global datacon
global jigsaw

terminal = None
jigsaw = None
settings = {}
db = None
locks = {}
datacon = None
rcat = None
tables = {}
location = {}
pchandler = None
game_loading = True
coordinator = None
total_pieces = 0

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
        global game_loading
        # TODO: userid and userid[0] is confusing 
        try:
            enc = json.loads(self.message)
            # send the config when the user joins
            if "NU" in enc:
                # get the user id
                new_user_list = enc["NU"]
                if len(new_user_list) != 1:
                    raise Exception('Not supporting multiple new users')
                userid = new_user_list[0]

                if not game_loading and enc["SS"] == rcat.pc.adm_id:
                    jigsaw.send_game_to_clients(userid)

            elif "UD" in enc:
                # User was disconnected. Inform other clients
                if enc["SS"] == rcat.pc.adm_id:
                    del enc["SS"]
                    datacon.mapper.disconnect_user(enc["UD"])
                    if enc["UD"] in locks:
                        pid = locks[enc["UD"]]
                        piece = datacon.mapper.get_piece(pid)
                        response = {'M': {'pd': {'id': piece.pid, 'x':piece.x, 'y':piece.y, 'b':piece.b, 'l':None}}}  #  no 'U' = broadcast
                        jsonmsg = json.dumps(response)
                        self.handler.write_message(jsonmsg)
                    
                    response = {'M': enc}
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)

            else:
                if game_loading:
                    msg = {'M': {'go':True}}
                    jsonmsg = json.dumps(msg)
                    pchandler.write_message(jsonmsg)
                    return

                # usual message
                logging.debug(enc["M"])
                m = json.loads(enc["M"])
                userid = enc["U"][0]

                if 'usr' in m:  # 1- client connects to server/opens websocket
                    # 2- server sends game state: 'c' config msg
                    # 3- client answers with its user name: 'usr' msg
                    # 4- server tells all clients about the new user: 'NU' msg 
                    if m['usr'] != 'Guest':  # guests don't have points 
                        update_res = datacon.mapper.new_user_connected(userid, m['usr'])
                        response = {'M': {'NU':update_res}}  # New User
                        jsonmsg = json.dumps(response)
                        self.handler.write_message(jsonmsg)

                elif 'pm' in m:  # piece movement
                    pid = m['pm']['id']
                    x = m['pm']['x']
                    y = m['pm']['y']
                    
                    ret = datacon.mapper.lock_piece(pid,userid)
                    if ret:
                        global locks
                        locks[userid] = pid

                    """
                    lockid = piece['l']
                    if (not lockid or lockid == "None") and not piece['b']:  # lock the piece if nobody owns it
                        global locks
                        lockid = userid
                        locks[userid] = piece
                        datacon.mapper.lock_piece(pid,lockid)
                        logging.debug('%s starts dragging piece %s' % (userid, pid))
                    """
                        
                    # update piece coords
                    datacon.mapper.move_piece(pid, {'x':x, 'y':y})
                    
                    # add lock owner to msg to broadcast
                    response = {'M': {'pm': {'id': pid, 'x':x, 'y':y, 'l':userid}}}  #  no 'U' = broadcast
                    
                    # broadcast
                    jsonmsg = json.dumps(response)
                    self.handler.write_message(jsonmsg)
                    
                elif 'pd' in m:  # piece drop
                    pid = m['pd']['id']
                    x = m['pd']['x']
                    y = m['pd']['y']

                    piece = datacon.mapper.get_piece(pid)
                    if not piece:
                        raise Exception("Could not retrieve piece for lock check.")
                    if not piece.l:
                        logging.warning("[jigsawapp]: Got something weird: %s" % piece)
                        return
                    
                    lockid = piece.l
                    if lockid and lockid == userid and not piece.b:  # I was the owner
                        if userid in locks:
                            del locks[userid]

                        # eventually bind piece 
                        bound = m['pd']['b']
                        if bound:  # we know the piece is not bound yet
                            logging.debug('%s bound piece %s at %d,%d'
                                      % (userid, pid, x, y))
                            datacon.mapper.bind_piece(pid,{'l':None, 'x':x, 'y':y, 'b':1})

                            # Update score board. Separate from 'pd' message because this is always broadcasted.
                            update_res = datacon.mapper.add_to_user_score(userid)
                            # If not update_res means we have an anonymous user, no scores should be sent
                            if update_res:
                                response = {'M': {'scu':update_res}}
                                jsonmsg = json.dumps(response)
                                self.handler.write_message(jsonmsg)

                        else:
                            # unlock piece and update piece coords
                            res = datacon.mapper.drop_piece(pid, {'l':None, 'x':x, 'y':y})
                            if res:
                                logging.debug('%s dropped piece %s at %d,%d'
                                          % (userid, pid, x, y))
                            else:
                                logging.error("[jigsaw]: Error dropping piece")
                    else:
                        logging.debug("[jigsaw]: Never got the lock, how odd.")
                    # add lock owner to msg to broadcast
                    response = {'M': {'pd': {'id': pid, 'x':x, 'y':y, 'b':bound, 'l':None}}}  #  no 'U' = broadcast
                    jsonmsg = json.dumps(response)
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
        self.datacon = datacon
        self.game_loading = game_loading
        rcat.pc.set_admin_handler(self.admin_parser)
        config = helper.open_configuration('jigsaw.cfg')
        settings = self.jigsaw_parser(config)
        helper.close_configuration('jigsaw.cfg')

        user = settings["db"]["user"]
        password = settings["db"]["password"]
        address = settings["db"]["address"]
        database = settings["db"]["db"]

        # Open connection to database and setup pool of connections. Makes datacon.db calls possible.
        datacon.db.open_connections(address, user, password, database)
        
        if settings["main"]["start"] == "true":
            # Leader is responsible to clear out all previous host data, and register as the first node 
            # Other nodes will only start after the leader is done clearing and registering. This happens when leader sends NEW game.
            datacon.mapper.cleanup_obm()
            settings["main"]["abandon"] = False
            self.start_game()

    def check_game_end(self):
        global settings
        global game_loading
        global total_pieces 
        total_pieces = int(grid['nrows']) * int(grid['ncols'])
        
        game_over = False
        while (not game_over):
            game_over = self.datacon.mapper.game_over(total_pieces)
            time.sleep(3)
                
        game_loading = True
        scores = datacon.mapper.get_user_scores(20)  # top 20 and connected player scores
        msg = {'M': {'go':True, 'scores':scores}}
        jsonmsg = json.dumps(msg)
        pchandler.write_message(jsonmsg)
        settings["main"]["abandon"] = True

        self.start_game()

    def send_game_to_clients(self, client=None):
        # TODO: Not send all pieces
        pieces = []
        while(not pieces):
            pieces = datacon.mapper.select_all()
        scores = datacon.mapper.get_user_scores(20)  # top 20 and connected player scores

        # send the board config
        cfg = {'img':img_settings,
               'board': board,
               'grid': grid,
               'frus': dfrus,
               'pieces': pieces,
               'scores' : scores
               }
        
        if not client:
            for client in scores['connected']:
                cfg['myid'] = client['uid'] 
                response = {'M': {'c': cfg}, 'U': [client['uid']]}
                jsonmsg = json.dumps(response)
                pchandler.write_message(jsonmsg)
        else:
            cfg['myid'] = client
            response = {'M': {'c': cfg}, 'U': [client]}
            jsonmsg = json.dumps(response)
            pchandler.write_message(jsonmsg)


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
        global game_loading
        global settings
        if "BC" in msg:
            if "NEW" in msg["BC"]:
                global board
                global img_settings
                global grid
                game_loading = True
                terminal.pause_terminal()

                # Tell mapper to register cacheable objects with the OBM. Only fires once.
                datacon.mapper.init_obm([User,Piece])

                if "C" in msg["BC"]:
                    global coordinator
                    coordinator = msg["BC"]["C"]
                    logging.info("[jigsawapp]: Coordinator is " + coordinator)

                newgame_settings = msg["BC"]["NEW"]
                board = newgame_settings["board"]
                img_settings = newgame_settings["img"]
                grid = newgame_settings["grid"]
                datacon.mapper.join(newgame_settings)
                if settings["main"]["start"] == "true":
                    logging.info("[jigsawapp]: Starting game, please wait...")
                    # Restarting the game at the user's command, or at game over             
                    if settings["main"]["abandon"]:
                        logging.info("[jigsawapp]: Abandoning old game.")
                        datacon.mapper.reset_game(keep_users=True)
                        settings["main"]["abandon"] = False

                    count = datacon.db.count(Piece)
                    if count > 0:
                            logging.info("[jigsawapp]: Recovering last game.")
                            datacon.mapper.recover_last_game()
                    else:
                        # Prepares the pieces in the database
                        pieces = []
                        for r in range(grid['nrows']):
                            for  c in range(grid['ncols']):
                                pid = str(uuid.uuid4())  # piece id
                                b = 0  # bound == correctly placed, can't be moved anymore
                                l = None # lock = id of the player moving the piece
                                x = randint(0, board['w'] - grid['cellw'])
                                y = randint(0, board['h'] - grid['cellh'])
                                
                                pieces.append(Piece(pid, x, y, c, r, b, l))
                                
                        datacon.mapper.create_pieces(pieces)

                    # Game end checker
                    t = Thread(target=self.check_game_end)
                    t.daemon = True
                    t.start()

                    # Tell servers that new game started
                    newmsg = {"BC":{"LOADED":True}}
                    json_message = json.dumps(newmsg)
                    proxy_admin = random.choice(rcat.pc.admin_proxy.keys())
                    proxy_admin.send(json_message)

                    # Tell clients about new game
                    self.send_game_to_clients()


            elif "LOADED" in msg["BC"]:
                game_loading = False
                logging.info("[jigsawapp]: Game has loaded. Have fun!")
                terminal.show_terminal()

    def start_game(self):
        global settings
        # Tells all other servers to start game and gives a fixed list of admins so that they all create the same Data Structure
        mod_settings = deepcopy(settings)
        del mod_settings["main"]["start"]
        mod_settings["ADMS"] = list(rcat.pc.admins)
        newmsg = {"BC":{"NEW":mod_settings, "C":rcat.pc.adm_id}}
        json_message = json.dumps(newmsg)
        proxy_admin = random.choice(rcat.pc.admin_proxy.keys())
        proxy_admin.send(json_message)
        

if __name__ == "__main__":
    logging.config.fileConfig("connector_logging.conf")
    rcat = RCAT(JigsawServerHandler, SQLAlchemyConnector, JigsawMapper, ObjectManager)
    datacon = rcat.datacon
    logging.debug('[jigsawapp]: Starting jigsaw..')

    time.sleep(2)

    jigsaw = JigsawServer()
    jigsaw._debug = lambda cmd: eval(cmd)
    terminal = helper.Terminal(jigsaw)
    terminal.run_terminal()
