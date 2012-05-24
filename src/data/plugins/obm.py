'''
Created on May 18, 2012

@author: arthur
'''
import json
import tornado.web
import urllib
import httplib
import logging

conn = None
pubsubs = None
mylocation = None
tables = None
location = None
obm = None
logger = logging.getLogger()

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
            obj = obm.relocate(tbl,rid,newowner)
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
    def __init__(self,myloc,r_tables,r_location):
        global mylocation
        global tables
        global location
        global obm
        obm = self
        mylocation = myloc
        tables = r_tables
        location = r_location

    """
    __relocate(self,table,rid,newowner): Relocates data to another app
    """
    def relocate(self,table,rid,newowner):
        try:
            if location[table][rid] == mylocation:
                cur = conn.cur
                mystr = "UPDATE {} SET __location__ = '{}' WHERE {} = {}".format(table,newowner,tables[table]["__ridname__"],`rid`)
                logger.debug(mystr)
                cur.execute(mystr)
                location[table][rid] = newowner
                return tables[table][rid]
            else:
                return location[table][rid]
        except Exception,e:
            logger.error(e)
            return "[Relocation failed]"
        
    """
    set_object_owner(self,table,RID,objects): Sets the location flag for items with the same desired RID to this location. 
    Objects are the MySQL query result of the selecting all rows with RID.
    """
    def set_object_owner(self,table,RID,objects):
        rid_name = tables[table]["__ridname__"]
        cur = conn.cur        
        cur.execute("UPDATE %s SET location = '%s' WHERE %s = %s".replace("'","`") % (table,mylocation,rid_name,RID)) #TODO: Concurrency?
        cur.connection.commit()
        location[table][RID] = mylocation
        for item in objects:
            del item["__location__"]
        tables[table][RID] = objects
        
    """
    request_relocate_to_local(self,table,rid): Requests that an object with rid is stored locally (i.e. same place as where
    the client is currently making requests to.
    """
    def request_relocate_to_local(self,table,rid):
        if not location[table][rid]:
            conn.select(table,rid)
        self.send_request_owner(location[table][rid],table,rid,"relocate")
        
    """
    __send_request_owner(self,host,table,RID,name,update_value): Sends message to authoritative owner of object to update the current value of object with id=RID
    """    
    def send_request_owner(self,obj_location,table,RID,op,names=None,update_tuples=None):
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
