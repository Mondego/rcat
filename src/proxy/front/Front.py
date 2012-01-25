import sys
import tornado.web
import tornado.websocket
import time
import Queue
from multiprocessing import Process
from common.message import MESSAGE_TYPE
from proxy.back.Back import ServerHandler 
import json

def SendToClient(handler,msg):
    handler.write(msg)

class Handler(tornado.web.RequestHandler):
    def get(self):
        SendToClient(self,"Hello World")
        
    def post(self):
        timestamp = time.time()
        argument = self.get_argument("message", False)
        if (argument):
            #self.write(argument + ";timestamp: " + str(timestamp))
            msg = argument + ";timestamp: " + str(timestamp)
            #pool.apply_async(SendToClient, (self,msg,))

class ClientHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print "WebSocket opened"
        
    def on_message(self, message):
        try:
            msg = json.loads(message)
            if msg["type"] == MESSAGE_TYPE.CONNECT:
                print "CONNECTING"
            ServerHandler.send_message(message)
        except Exception as inst:
            self.write_message("Not valid JSON")
            print inst

    def on_close(self):
        print "WebSocket closed"
        
    def accept_client(self,client,handler):
        

class ClientLayer():
    dq = {}
    
    def __init__(self):
        p = Process(target=SendLoop, args=(self.dq,))
        p.start()
        
    def ClientConnect(self, userid):
        self.dq[userid] = Queue()



def SendLoop(dq):
    for client in dq:
        #Send message to client
        print "Hey"
        pass
