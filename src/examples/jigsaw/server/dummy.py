from random import randint
from time import sleep
import json
import logging.config
import tornado.ioloop
import tornado.web
import tornado.websocket
import uuid

log = logging.getLogger('dummysrv')

img_url = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_1MB.jpg'
board = {'w': 2000,
         'h': 1600,
         'maxScale': 8,
         'minScale': 0.5
         }
grid = {'x': 250,
        'y': 200,
        'ncols': 4,
        'nrows': 4,
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
for r in range(grid['nrows']):
    for  c in range(grid['ncols']):
        pid = str(uuid.uuid4())
        p = {'id': pid,
             'b': False, # bound == correctly placed, can't be moved anymore
             'x': randint(0, board['w'] / 2),
             'y': randint(0, board['h'] / 2),
             'c': c,
             'r': r
             }
        pieces[pid] = p

clients = {}


class WSHandler(tornado.websocket.WebSocketHandler):


    def open(self):
        """ memorize client and send puzzle init config. """
        # memorize client from its ip and port
        myid = str(self.request.connection.address)
        self.myid = myid
        global clients
        clients[myid] = self
        log.info(myid + ' joined')
        self.frus = dfrus # to be updated by the client when it receives the msg
        # send puzzle config data
        cfg = {'imgurl':img_url,
               'board': board,
               'grid': grid,
               'frus': dfrus,
               'pieces': pieces
               }
        msg = {'c': cfg}
        self.write_message(json.dumps(msg))


    def on_message(self, msg):
        """ """
        m = json.loads(msg)
        if 'rp' in m: # frustum update
            self.frus = m['rp']['v']
            # TODO: send pieces located in the new frustum 
        elif 'p' in m: # piece movement
            # update piece location on the server-side
            pid = m['p']['id']
            x, y = m['p']['x'], m['p']['y']
            global pieces
            pieces[pid]['x'] = x
            pieces[pid]['y'] = y
            # TODO: check if piece correctly placed, and eventually bound
            # forward piece movement to everyone
            for c in clients.values():
                c.write_message(json.dumps(m))


    def on_close(self):
        """ remove from clients """
        myid = self.myid
        global clients
        del clients[myid]
        log.info(myid + ' left')



handlers = (r'/test', WSHandler),
app = tornado.web.Application(handlers)


if __name__ == "__main__":
    logging.config.fileConfig("logging.conf")
    app.listen(9000) # TODO: from config file instead 
    log.info('server listens on 9000')
    tornado.ioloop.IOLoop.instance().start()

