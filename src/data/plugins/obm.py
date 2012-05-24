'''
Created on May 18, 2012

@author: arthur
'''
import json
import tornado.web
import urllib
import httplib

conn = None
pubsubs = None
mylocation = None

class OBMHandler(tornado.web.RequestHandler):
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
            
class ObjectManager():
    def __init__(self,loc):
        global mylocation
        mylocation = loc
        
    """
    __send_request_owner(self,host,table,RID,name,update_value): Sends message to authoritative owner of object to update the current value of object with id=RID
    """    
    def __send_request_owner(self,obj_location,table,RID,op,names=None,update_tuples=None):
        host,port = obj_location.split(':')
        if op == "update":
            cmd = "&op=update&tuples=" + urllib.quote(json.dumps(update_tuples))
        elif op == "select":
            cmd = "&op=select"
            if names:
                cmd += "&names=" + urllib.quote(json.dumps(names))
        elif op == "relocate":
            cmd = "&op=relocate&no=" + mylocation
        conn = httplib.HTTPConnection(host,port)
        conn.request("GET", "/obm?rid="+str(RID)+"&tbl="+table+cmd)
        resp = conn.getresponse()
        if update_tuples:
            if resp.status.startswith("200"):
                if resp.read() == "OK":
                    return True
                else:
                    return False
            else:
                return False
        else:
            result = resp.read()
            return result
