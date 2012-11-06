from threading import Thread, current_thread
import argparse
import logging.config
import time
import websocket

URL = "ws://localhost:9000/ws"
MSGDELAY = 0.1 # delay between two messages
NUMMSG = 10 # how many msgs to send
BOTDELAY = 0.5 # delay between 2 bot creations
NUMBOTS = 2 # how many bots to create

log = logging.getLogger('client')


def on_message(ws, msg):
    #print '%s \t %s MSG: %s' % (time.time(), current_thread().name, msg)
    pass

def on_error(ws, error):
    tname = current_thread().name
    log.error('%s ERROR: %s' % (tname, error))

def on_close(ws):
    tname = current_thread().name
    log.info('%s CLOSED' % (tname))

def on_open(ws):
    rcvthname = current_thread().name
    botnum = int(rcvthname[4:]) # remove 'recv' from the beginning of the thread name 
    def startsend(*args):
        thname = current_thread().name
        for i in range(NUMMSG):
            txt = "I'm bot%d and this is msg %d" % (botnum, i)
            ws.send(txt)
            #print '%s \t %s SENT: %s' % (time.time(), thname, txt)
            time.sleep(MSGDELAY)
        ws.close()
    th = Thread(target=startsend)
    th.name = 'send%s' % botnum
    th.start()


if __name__ == "__main__":
    # example usage: for 2 bots sending 50 msgs
    # with one msg sent every 0.05 sec, and 0.5 sec between 2 bot creations
    # python client.py -n 2 -m 50 -bd 0.5 -md 0.05

    websocket.enableTrace(False)

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', type=int, help='number of bots', default=NUMBOTS)
    parser.add_argument('-bd', type=float, help='delay between 2 bots', default=BOTDELAY)
    parser.add_argument('-m', type=int, help='number of msgs', default=NUMMSG)
    parser.add_argument('-md', type=float, help='delay between 2 msgs', default=MSGDELAY)

    args = vars(parser.parse_args()) # returns a namespace converted to a dict)

    numbots = args['n']
    botdelay = args['bd']
    NUMMSG = args['m']
    MSGDELAY = args['md']

    logging.config.fileConfig("logging.conf")

    websocks = []
    try:
        for botnum in range(numbots):
            ws = websocket.WebSocketApp(URL,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
            websocks.append(ws)
            th = Thread(target=ws.run_forever) # rcv thread
            th.name = 'recv%d' % botnum
            th.start()
            log.info('bot%d created' % botnum)
            time.sleep(botdelay)

    except KeyboardInterrupt: # close all websockets
        for ws in websocks:
            ws.close()
            log.info('%s closed' % ws)

# TODO: ctrl-C triggers "AttributeError: 'NoneType' object has no attribute 'send'"
 
