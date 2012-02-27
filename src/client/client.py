from time import sleep
from ws4py.client.threadedclient import WebSocketClient
import logging.config

log = logging.getLogger('client')

class Spawner():
    
    def __init__(self):
        
        # TODO: read from config file
        NUMBOTS = 1
        DELAY = 1 #DELAY between bot connections, in seconds
        ADDR = 'http://localhost:9000/ws'
        FREQ = 1 # number of msg to send per sec
        DURATION = 5 # how long the bots should be running for, in seconds
        
        # create all the bots
        self.bots = []

        for botnum in range(NUMBOTS):
            bot = Bot(botnum, FREQ, DURATION, ADDR)
            self.bots.append(bot)
            bot.connect()
            sleep(DELAY)
            
        
    
class Bot(WebSocketClient):
    # WebSocketClient from https://github.com/Lawouach/WebSocket-for-Python
    def __init__(self, myid, f, dur, addr):
        WebSocketClient.__init__(self, addr)
        # TODO: send msg at frequency f, and during dur seconds
        self.f = f
        self.dur = dur
        self.myid = myid
 
        
    
    def opened(self):
        log.info('opened')
        
        sleep(2) # TODO: this sleep seems to prevent received_message to be triggered - how is the threading happening?
        num_msg_to_send = self.f * self.dur
        for i in range(num_msg_to_send):
            self.send('my name is ' + str(self.myid) + ' and this is msg# ' + str(i))
            sleep(1. / self.f)
        



    def closed(self, code, reason):
        log.info("Closed")


    def received_message(self, m):
        log.debug("Received " + str(m))
        self.close()

if __name__ == '__main__':
    logging.config.fileConfig("logging.conf")
    Spawner()


