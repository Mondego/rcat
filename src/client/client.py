from threading import Thread
import logging.config
import time
import websocket
import argparse

# TODO: argparse those constants
DELAY = 1 # delay between sending 2 msgs, in seconds
NUMMSG = 3 #  how many msg to send
URL = "ws://localhost:9000/ws"

log = logging.getLogger('client')
keep_running = True


def connect_task(**kwargs):
    """ connect to server,
    send 3 msgs,
    then close ws
    """
    ws = kwargs['ws']
    botnum = kwargs['botnum']

    ws.connect(URL) # this blocks until the server replies
    log.debug('connected')
    # start listening
    Thread(target=rcv_task).start()
    # start sending
    try: 
        for i in range(NUMMSG):
            msg = 'hello#%d from bot#%d' % (i, botnum)
            ws.send(msg)
            log.debug('sent: ' + msg)
            time.sleep(DELAY)
    except IOError, e:
        log.error('socket closed unexpectedly while writing: %s', e)
    # done sending: close ws
    global keep_running
    keep_running = False
    ws.close()
    log.debug('closed')


def rcv_task():
    try:
        while keep_running:
            data = ws.recv()
            if data: # sometimes, recv returns None
                log.debug("rcvd: %s" % data)
    except IOError, e:
        if keep_running: # socket was closed under our feet
            log.error('socket closed unexpectedly while reading: %s', e)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run some bots.')
    parser.add_argument('-n', type=int, help='number of bots', default=1)

    args = parser.parse_args() # returns a namespace
    args = vars(args) # convert to dict

    logging.config.fileConfig("logging.conf")
    websocket.enableTrace(False)

    numbots = args['n']
    websocks = [] # keep track of the websockets used

    try:
        for botnum in range(numbots):
            ws = websocket.WebSocket()
            websocks.append(ws)
            args = {'ws':ws, 'botnum':botnum}
            Thread(target=connect_task, kwargs=args).start()
            time.sleep(DELAY) # wait a bit before starting the next bot
            # main thread dies after all bots have sent their msgs
        #time.sleep(numbots + NUMMSG * DELAY + 1)
        time.sleep(10) 
    except KeyboardInterrupt:
        # close all websockets
        for ws in websocks:
            ws.close()

