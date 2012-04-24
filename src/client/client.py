from threading import Thread
import logging.config
import time
import websocket
import argparse

# TODO: argparse those constants
DELAY = 1 # delay between sending 2 msgs, in seconds
NUMMSG = 3 # how many msg to send
URL = "ws://localhost:9000/ws"
NUMBOTS = 2
WITHTRACE = True

log = logging.getLogger('client')


def connect_task(**kwargs):
    """ connect to server,
    send 3 msgs,
    then close ws
    """
    ws = kwargs['ws']
    botnum = kwargs['botnum']

    ws.connect(URL) # this blocks until the server replies
    log.debug('%2d connected' % botnum)
    # start listening
    th = Thread(target=rcv_task, kwargs={'botnum':botnum})
    th.name = 'th_rcv%d' % botnum
    th.start()
    # start sending
    try: 
        for i in range(NUMMSG):
            msg = 'hello#%d from bot#%d' % (i, botnum)
            log.debug('%2d send: %s' % (botnum, msg))
            ws.send(msg)
            time.sleep(DELAY)
    except IOError, e:
        log.error('%2d socket closed unexpectedly while writing: %s',
                  (botnum, e))
    # done sending: close ws
    global keep_running
    keep_running[botnum] = False # will cause the rcving thread to close the ws
    
    ws.close()
    log.debug('%2d closed' % botnum)

def rcv_task(botnum= -1):
    try:
        while keep_running[botnum]:
            data = ws.recv()
            if data: # sometimes, recv returns None
                #log.debug("%2d rcvd: %s" % (botnum, data))
                pass        
#        ws.close() # closing multiple times is OK
#        log.debug('%2d closed in rcver' % botnum)
    except IOError, e:
        if keep_running[botnum]: # socket was closed under our feet
            log.error('%2d socket closed unexpectedly while reading: %s',
                      (botnum, e))



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', type=int, help='number of bots', default=NUMBOTS)

    args = parser.parse_args() # returns a namespace
    args = vars(args) # convert to dict

    logging.config.fileConfig("logging.conf")
    websocket.enableTrace(WITHTRACE)
    
    numbots = args['n']
    websocks = [] # keep track of the websockets used
    
    keep_running = [True] * numbots
    
    try:
        for botnum in range(numbots):
            ws = websocket.WebSocket()
            websocks.append(ws)
            args = {'ws':ws, 'botnum':botnum}
            th = Thread(target=connect_task, kwargs=args)
            th.name = 'th_co%d' % botnum
            th.start()
            time.sleep(DELAY * 1.5) # wait a bit before starting the next bot
            # main thread dies after all bots have sent their msgs
        #time.sleep(numbots + NUMMSG * DELAY + 1)
        time.sleep(5)
    except KeyboardInterrupt:
        # close all websockets
        for ws in websocks:
            ws.close()
            print '%2d closed' % ws

