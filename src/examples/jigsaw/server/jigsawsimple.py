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
import uuid
from random import randint

global datacon

datacon = None
pc = None
appip = None
appport = None



log = logging.getLogger('dummysrv')

img_url = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_1MB.jpg'
board = {'w': 2000,
         'h': 1600,
         'maxScale': 16,
         'minScale': 0.5
         }
grid = {'x': 250,
        'y': 200,
        'ncols': 2,
        'nrows': 2,
        'cellw': 100,
        'cellh': 75
        }
# default frustum; w and h are determined by each client's canvas size
dfrus = {'x': 0,
         'y':0,
         'scale':1,
         'w': None,
         'h': None
         }

pieces = {}

clients = {}

class EchoWebSocket(websocket.WebSocketHandler):
    def open(self):
        # handler for the connection to the proxy
        logging.debug("App Websocket Open")
        datacon.db.open_connections('opensim.ics.uci.edu', 'rcat', 'isnotamused', 'rcat')
        datacon.mapper.create_table("jigsawPieces", "pid")
        # the table has to be created beforehand with the correct columns
        # outside of the app, manually
        # TODO: build the table procedurally
        # columns are: id,b,x,y,c,r,l
        datacon.db.execute("delete from jigsawPieces")

        # make pieces
        for r in range(grid['nrows']):
            for  c in range(grid['ncols']):
                pid = str(uuid.uuid4()) # piece id
                b = 0 # bound == correctly placed, can't be moved anymore
                l = None# lock = id of the player moving the piece
                x = randint(0, board['w'] / 2)
                y = randint(0, board['h'] / 2)
                values = [pid, b, x, y, c, r, l]
                datacon.mapper.insert('jigsawPieces', values, pid)



    def on_message(self, message):
        try:
            enc = json.loads(message)

            # send the config when the user joins
            if "NU" in enc:
                # get the user id
                userid = enc["NU"]

                # TODO: mapper should provide "select * from jigsawPieces"
                # these lines are a temporary hack to get data correctly formated 
                pieces = datacon.mapper.tables["jigsawPieces"]
                pieces = pieces.copy()
                for key in ['__columns__', "__metadata__", "__ridname__"]:
                    try:
                        del(pieces[key])
                    except KeyError:
                        pass
                for pid in pieces.keys():
                    pieces[pid] = pieces[pid][0]

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
                    piece = datacon.mapper.select('jigsawPieces', pid)[0]
                    lockid = piece['l']
                    if not lockid: # lock the piece if nobody owns it
                        datacon.mapper.update('jigsawPieces', [('l', userid)], pid)
                        log.debug('%s starts dragging piece %s' % (userid, pid))
                    if lockid == userid: # change location if I'm the owner
                        # update piece coords
                        x = m['pm']['x']
                        datacon.mapper.update('jigsawPieces', [('x', x)], pid)
                        y = m['pm']['y']
                        datacon.mapper.update('jigsawPieces', [('y', y)], pid)
                        # add lock owner to msg to broadcast
                        response = {'M': {'pm': {'id': pid, 'x':x, 'y':y, 'l':lockid}}} #  no 'U' = broadcast
                        # broadcast
                        self.write_message(json.dumps(response))

                elif 'pd' in m: # piece drop
                    pid = m['pd']['id']
                    piece = datacon.mapper.select('jigsawPieces', pid)[0]
                    lockid = piece['l']
                    if lockid and lockid == userid: # I was the owner
                        # unlock piece
                        datacon.mapper.update('jigsawPieces', [('l', None)], pid)
                        # update piece coords
                        x = m['pd']['x']
                        datacon.mapper.update('jigsawPieces', [('x', x)], pid)
                        y = m['pd']['y']
                        datacon.mapper.update('jigsawPieces', [('y', y)], pid)

                        # eventually bind piece 
                        bound = m['pd']['b']
                        if bound:
                            log.debug('%s bound piece %s at %d,%d'
                                      % (userid, pid, x, y))
                            datacon.mapper.update('jigsawPieces', [('b', 1)], pid)
                        else:
                            log.debug('%s dropped piece %s at %d,%d'
                                      % (userid, pid, x, y))
                        # add lock owner to msg to broadcast
                        response = {'M': {'pd': {'id': pid, 'x':x, 'y':y, 'b':bound, 'l':None}}} #  no 'U' = broadcast
                        self.write_message(json.dumps(response))

        except Exception as e:
            logging.error(e)
            return False


    def on_close(self):
        logging.debug("App WebSocket closed")


handlers = [
    (r"/", EchoWebSocket)
]

if __name__ == "__main__":
    appip, appport, proxies = helper.parse_input('jigsawapp.cfg')
    logging.config.fileConfig("connector_logging.conf")
    logging.debug('[demoapp]: Starting app in ' + appip + ":" + appport)
    # TODO: Allow passing of options to determine which mapper and db to use. For now, hardcoded
    datacon = DataConn.DataConnector("ChatManagerByID", appip + ":" + appport)
    datacon.db = MySQLConnector(datacon)
    datacon.mapper = ChatManager(datacon)
    datacon.obm = ObjectManager(datacon, handlers)

    application = tornado.web.Application(handlers)
    application.listen(appport)

    t = Thread(target=tornado.ioloop.IOLoop.instance().start)
    t.daemon = True
    t.start()
    pc = ProxyConnector(["ws://chateau.ics.uci.edu:8888"], "ws://" + appip + ':' + appport)
    helper.terminal()

