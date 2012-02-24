from ws4py.client.threadedclient import WebSocketClient



class EchoClient(WebSocketClient):
    # from https://github.com/Lawouach/WebSocket-for-Python
    def opened(self):
        print 'send hello from bot'
        self.send('Hello from bot')

    def closed(self, code, reason):
        print "Closed ", code, reason

    def received_message(self, m):
        print "Received ", str(m)
        self.close()

if __name__ == '__main__':
    try:
        ws = EchoClient('http://localhost:9000/ws', protocols=['http-only', 'chat'])
        ws.connect()
    except KeyboardInterrupt:
        ws.close()


