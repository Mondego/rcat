from ws4py.client.threadedclient import WebSocketClient
from time import sleep

class Spawner():
    
    def __init__(self):
        
        # TODO: read from config file
        NUMBOTS = 3
        DELAY = 1 #DELAY between bot connections, in seconds
        ADDR = 'http://localhost:9000/ws'
        FREQ = 20 # number of msg to send per sec
        DURATION = 5 * 60 # how long the bots should be running for, in seconds
        
        # create all the bots
        self.bots = []

        for i in range(NUMBOTS):
            bot = Bot(i, FREQ, DURATION, ADDR)
            self.bots.append(bot)
            bot.connect()
            sleep(DELAY)
            
        
    
class Bot(WebSocketClient):
    # WebSocketClient from https://github.com/Lawouach/WebSocket-for-Python
    def __init__(self, id, f, dur, addr):
        WebSocketClient.__init__(self, addr)
        # TODO: send msg at frequency f, and during dur seconds
 
        
    
    def opened(self):
        print 'send hello from bot'
        self.send('Hello from bot')

    def closed(self, code, reason):
        print "Closed ", code, reason

    def received_message(self, m):
        print "Received ", str(m)
        self.close()

if __name__ == '__main__':
    Spawner()


