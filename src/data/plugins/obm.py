'''
Created on May 18, 2012

@author: arthur
'''
import json
import tornado.web

conn = None
pubsubs = None

class ObjectManager(tornado.web.RequestHandler):
    def initialize(self, connector, pubsub_list = None):
        global conn
        global pubsubs
        conn = connector
        pubsubs = pubsub_list
    
    def get(self):
        # Constraint! RID is always an INT
        rid = int(self.get_argument("rid",None))
        tbl = self.get_argument("tbl",None)
        op = self.get_argument("op",None)
        if op == "update":
            tuples = json.loads(self.get_argument("tuples"),None)   
            conn.update(tbl,tuples,rid)
            self.write("OK")
        elif op == "select":
            jnames = None
            names = self.get_argument("names",None)
            if names:
                jnames = json.loads(names)
            obj = conn.select(tbl,rid,jnames)
            jsonmsg = json.dumps(obj)
            self.write(jsonmsg)
        elif op == "relocate":
            newowner = self.get_argument("no",None)
            obj = conn.relocate(tbl,rid,newowner)
            jsonmsg = json.dumps(obj)
            self.write(jsonmsg)
        elif op == "subscribe":
            ip =  self.request.remote_ip
            port = self.get_argument("port",None)
            interests = json.loads(self.get_argument("interests",None))
            loc = (ip,port)
            if pubsubs:
                pubsubs[tbl].add_subscriber(loc,interests) 
            
