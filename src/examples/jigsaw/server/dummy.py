from random import randint
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
for r in range(grid['nrows']):
    for  c in range(grid['ncols']):
        pid = str(uuid.uuid4())
        p = {'id': pid,
             'b': False, # bound == correctly placed, can't be moved anymore
             'x': randint(0, board['w'] / 3),
             'y': randint(0, board['h'] / 3),
             'c': c,
             'r': r,
             'l': None # lock = id of the player moving the piece
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
               'pieces': pieces,
               'myid': self.myid
               }
        msg = {'c': cfg}
        self.write_message(json.dumps(msg))



    def on_message(self, msg):
        """ """
        m = json.loads(msg)
        global pieces

        if 'rp' in m: # frustum update
            self.frus = m['rp']['v']
            # TODO: send pieces located in the new frustum

        elif 'pm' in m: # piece movement
            pid = m['pm']['id']
            lockid = pieces[pid]['l']
            if not lockid: # lock the piece if nobody owns it 
                pieces[pid]['l'] = self.myid
                log.debug('%s starts dragging piece %s' % (self.myid, pid))
            if lockid == self.myid: # change location if I'm the owner
                pieces[pid]['x'] = m['pm']['x']
                pieces[pid]['y'] = m['pm']['y']
                m['pm']['l'] = pieces[pid]['l'] # add the lock owner to the msg
                self.bc_json(m) # forward piece movement to everyone

        elif 'pd' in m: # piece drop
            pid = m['pd']['id']
            lockid = pieces[pid]['l']
            if not lockid or lockid == self.myid: # I (or no one) was the owner
                m['pd']['l'] = pieces[pid]['l'] # add the lock owner to the msg
                pieces[pid]['l'] = None
                x, y = m['pd']['x'], m['pd']['y']
                pieces[pid]['x'], pieces[pid]['y'] = x, y
                if m['pd']['b']:
                    log.debug('%s bound piece %s at %d,%d'
                              % (self.myid, pid, x, y))
                    pieces[pid]['b'] = True
                else:
                    log.debug('%s dropped piece %s at %d,%d'
                              % (self.myid, pid, x, y))

                self.bc_json(m) # forward piece drop to everyone


    def bc_json(self, msg):
        """ convert msg into JSON and broadcast it """
        for c in clients.values():
            c.write_message(json.dumps(msg))


    def on_close(self):
        """ remove from clients """
        myid = self.myid
        global clients
        del clients[myid]
        log.info(myid + ' left')



handlers = (r'/client', WSHandler),
app = tornado.web.Application(handlers)


if __name__ == "__main__":
    logging.config.fileConfig("logging.conf")
    app.listen(8888) # TODO: from config file instead 
    log.info('server listens on 8888')
    tornado.ioloop.IOLoop.instance().start()

