import signal
import socket
import threading
import time
import uuid
import websocket2


ADDR = 'ws://localhost:8889/'
SEND_FREQ = 20 # msgs per sec
MEASURE_FREQ = SEND_FREQ # measure every second


class Bot():
    """ Dummy bot tracking RTT using messages exchanged with an echo server. """

    def __init__(self):
        """ Initialize the sending and receiving parts. """
        sockopt = ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
                   (socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1),)
        self.ws = websocket2.create_connection(ADDR, sockopt=sockopt)
        print 'opened websocket'
        self.running = True
        self.sent_messages = {}
        self.measuring_counter = MEASURE_FREQ
        self.recver = threading.Thread(target=self.do_recv)
        self.recver.daemon = True

    def start(self):
        """ Start the receiver thread and start sending messages. """
        self.recver.start()
        while self.running:
            time.sleep(1. / SEND_FREQ)
            msg = str(uuid.uuid4()) * 30
            self.measuring_counter -= 1
            if self.measuring_counter == 0:
                self.measuring_counter = MEASURE_FREQ
                self.sent_messages[msg] = time.time()
                #print 'sent RTT probe ...'
            self.ws.send(msg)
        self.ws.close()
        print 'closed websocket'


    def do_recv(self):
        """ Periodically send a uuid as a msg to the server.
        This thread will die when self.running becomes False """
        while self.running:
            result = self.ws.recv() # blocking op
            if result in self.sent_messages: # this is a msg I sent before
                now = time.time()
                delay = now - self.sent_messages[result]
                del self.sent_messages[result]
                print 'latency is    %3.2f ms' % (delay * 1000)


    def on_killed(self, signum, frame):
        """ cf http://docs.python.org/2/library/signal.html#example """
        print 'closing...'
        self.running = False


if __name__ == "__main__":
    bot = Bot()
    # register signal handlers
    signal.signal(signal.SIGINT, bot.on_killed)
    signal.signal(signal.SIGQUIT, bot.on_killed)
    signal.signal(signal.SIGHUP, bot.on_killed) # when killed within the screen command
    signal.signal(signal.SIGTERM, bot.on_killed)
    bot.start()
