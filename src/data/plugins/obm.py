'''
Created on May 18, 2012

@author: arthur
'''
import json
import tornado.web
import urllib
import httplib
import logging
from threading import Thread
from tornado.ioloop import IOLoop
from multiprocessing.pool import ThreadPool
from tornado.web import asynchronous

obm = None
logger = logging.getLogger()

class OBMHandler(tornado.web.RequestHandler):
    
    def initialize(self):
        global pubsubs
        pubsubs = {}
        
    @asynchronous
    def get(self):
        # TODO: Worker threads to save hassle of starting threads
        OBMParser(self).start()
        

class OBMParser(Thread):
    def __init__(self,handler):
        Thread.__init__(self)
        self.handler = handler
                
    def run(self):
        rid = self.handler.get_argument("rid",None)
        tbl = self.handler.get_argument("tbl",None)
        op = self.handler.get_argument("op",None)
        if op == "update":
            tuples = json.loads(self.handler.get_argument("tuples"),None)
            obm.update(tbl,tuples,rid)
            IOLoop.instance().add_callback(self.reply("OK"))
        elif op == "insert":
            values = json.loads(self.handler.get_argument("values"),None)
            res = obm.insert(tbl,values,rid)
            if res:
                IOLoop.instance().add_callback(self.reply("OK"))
            else:
                IOLoop.instance().add_callback(self.reply("FAIL"))
        elif op == "select":
            #names = self.get_argument("names",None)
            #if names:
            #    jnames = json.loads(names)
            obj = obm.select(tbl,rid)
            jsonmsg = json.dumps(obj)
            IOLoop.instance().add_callback(self.reply(jsonmsg))
        elif op == "relocate":
            newowner = self.handler.get_argument("no",None)
            obj = obm.relocate(tbl,rid,newowner)
            jsonmsg = json.dumps(obj)
            IOLoop.instance().add_callback(self.reply(jsonmsg))
        elif op == "subscribe":
            ip =  self.handler.request.remote_ip
            port = self.handler.get_argument("port",None)
            interests = json.loads(self.handler.get_argument("interests",None))
            loc = (ip,port)
            if pubsubs:
                pubsubs[tbl].add_subscriber(loc,interests) 
    
    def reply(self,message):
        def _write():
            self.handler.write(message)
            self.handler.flush()
            self.handler.finish()
        return _write
    
    def on_complete_all(self):
        self.handler.finish()
        
            
class ObjectManager():
    datacon = None
    myid = None
    myhost = None
    tables = {}
    location = {}
    ridnames = {}
    indexes = {}
    columns = {}
    autoinc = {}
    
    def __init__(self,datacon,rid_type=None):
        global obm
        obm = self
        self.myid = datacon.myid
        self.myhost = datacon.host
        self.datacon = datacon
        self.tables = {}
        self.location = {}
        
    def register_node(self,adm,table,ridname,rid_type=None,autoinc=None):
        if not rid_type:
            rid_type = "varchar(255)"
        if autoinc != None:
            self.autoinc[table] = autoinc
        """
        cmd = "create table if not exists " + table + "_obm(rid " + rid_type + " not null,host varchar(255) not null, primary key(rid))"
        self.datacon.db.execute(cmd)
        cmd = "create table if not exists " + table + "_reg(admid varchar(255) not null,host varchar(255) not null, primary key(admid))"
        self.datacon.db.execute(cmd)
        cmd = "insert into " + table + "_reg values('" + adm + "','" + self.datacon.host + "')"
        self.datacon.db.execute(cmd)
        self.datacon.db.retrieve_table_meta(table+"_obm", "rid")
        self.datacon.db.retrieve_table_meta(table+"_reg", "admid")
        """
        
        cmd = "create table if not exists " + table + "_obm(rid " + rid_type + " not null,host varchar(255) not null, primary key(rid))"
        self.datacon.db.create_table(table+"_obm",cmd,"rid")
        cmd = "create table if not exists " + table + "_reg(admid varchar(255) not null,host varchar(255) not null, primary key(admid))"
        self.datacon.db.create_table(table+"_reg",cmd,"admid")
        cmd = "insert into " + table + "_reg values('" + adm + "','" + self.datacon.host + "')"
        self.datacon.db.execute(cmd)
        
        self.tables[table] = {}
        self.location[table] = {}
        self.ridnames[table] = ridname
        self.indexes[table] = {}
        self.columns[table] = self.datacon.db.tables_meta[table]["columns"]
    
    def clear(self,table):
        cmd = "drop table if exists " + table + "_obm"
        self.datacon.db.execute(cmd)
        cmd = "drop table if exists " + table + "_reg"
        self.datacon.db.execute(cmd)
        return True
    
    def find_all(self,table):
        # TODO: There is still possible inconsistency, current frustrum must be subscribing to updates
        # maybe also we need timestamps..
        cmd = "select * from " + table + "_obm"
        result = self.datacon.db.execute(cmd)
        logger.debug("[obm]: Result from select all in table_obm: " + str(result))
        return result
        
    def create_index(self,table,idxname):
        self.indexes[table][idxname] = {}
            
    def setowner(self,table,rid,values=None,owner=None,insert=None):
        if not owner:
            owner = self.myhost
#        else:
#            owner = self.gethost(table,owner)
        try:
            if not self.tables[table]:
                self.tables[table] = {}
            if not insert:
                self.datacon.db.schedule_update(table+"_obm",rid,{'host':owner})
            else:
                self.datacon.db.insert(table+"_obm",[rid,owner])
            self.tables[table][rid] = {}
            
            if values:
                if type(values) is dict:
                    self.tables[table][rid] = values
                else:
                    for name,idx in self.columns[table].items():
                        self.tables[table][rid][name] = values[idx]
            self.location[table][rid] = owner
        except Exception, e:
            logger.exception("[obm]: Failed to set owner in database.")
            return False
        
    """
    Local requests. When called, they will relocate objects locally if needed
    """
    def insert(self,table,values,rid=None):
        if table in self.autoinc:
            values.insert(self.autoinc[table],'NULL')
            res = self.datacon.db.insert(table,values,True)
            # rid is in autoinc
            if not rid:
                rid = res
            values[self.autoinc[table]] = res 
        else:
            if not rid:
                raise
            self.datacon.db.insert(table,values,False)
        
        self.setowner(table,rid,values,None,True)
        
        # Updates secondary indexes
        for idx in self.indexes[table].keys():
            value = values[self.columns[table][idx]]
            if value in self.indexes[table][idx]:
                self.indexes[table][idx][value].append(rid)
            else:
                self.indexes[table][idx][value] = [rid]
        return True

    def update(self,table,update_tuples,rid):
        # If I don't know where it is, find it in the database
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        
        if not self.location[table][rid] == self.myhost:
            # If I don't own it, but I should! Request relocation
            result = "Failed"
            while (result == "Failed"):
                self.location[table][rid] = self.getlocation(table,rid)
                if self.location[table][rid] == self.myhost: # we were just outdated, its here now, so all is good!
                    break
                else:
                    result = self.send_request_owner(self.location[table][rid],table,rid,"relocate")
            self.location[table][rid] = self.myhost
            
            if result != "Failed":
                # We got a reply! Lets decode it
                self.tables[table][rid] = json.loads(result)
            
        # If I own it but I don't have it in memory, fetch from database
        if not rid in self.tables[table]:
            cmd = "select * from " + table + " where " + self.ridnames[table] + " = " + rid
            # TODO: This will only return one result in every select! 
            self.tables[table][rid] = self.datacon.db.execute_one(cmd)
        
        for item in update_tuples:
            self.tables[table][rid][item[0]] = item[1]
        
        # Schedules update to be persisted.
        self.datacon.db.schedule_update(table,rid,self.tables[table][rid])
        
        return self.tables[table][rid]
    
    def select(self,table,rid):
        # If I don't know where it is, find it in the database
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        
        if not self.location[table][rid] == self.myhost:
            # If I don't own it, but I should! Request relocation
            result = "Failed"
            while (result == "Failed"):
                self.location[table][rid] = self.getlocation(table,rid)
                if self.location[table][rid] == self.myhost: # we were just outdated, its here now, so all is good!
                    break
                else:
                    result = self.send_request_owner(self.location[table][rid],table,rid,"relocate")
            self.location[table][rid] = self.myhost            
            if result != "Failed":
                # We got a reply! Lets decode it 
                self.tables[table][rid] = json.loads(result)
    
        # If I own it but I don't have it in memory, fetch from database
        if not rid in self.tables[table] or not self.tables[table][rid]:
            cmd = "select * from " + table + " where `" + str(self.ridnames[table]) + "` = '" + rid + "'"
            # TODO: This will only return one result in every select! 
            self.tables[table][rid] = self.datacon.db.execute_one(cmd)

        return self.tables[table][rid]
        
    def delete(self,table,rid):
        # If I don't know where it is, find it in the database
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        
        if not self.location[table][rid] == self.myhost:
            self.location[table][rid] = self.getlocation(table,rid)
            if not self.location[table][rid] == self.myhost:
                return "Failed"
            else:
                self.datacon.db.delete(table,rid)
                del self.location[table][rid]
                if rid in self.tables[table]:
                    del self.tables[table][rid]
                return True
        
    """
    Remote requests
    """
        
    def insert_remote(self,table,admid,values,rid):
        remotehost = self.gethost(table,admid)
        self.location[table][rid] = remotehost
        self.send_request_owner(remotehost, table, rid, "insert",values)
        logging.debug("[obm]: Inserting remotely at " + remotehost + " the values: " + str(values))
        return True
        
    def update_remote(self,table,admid,tuples,rid):
        remotehost = self.gethost(table,admid)
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        if self.location[table][rid] == self.myhost:
            self.setowner(table,rid,None,remotehost)
        
        self.location[table][rid] = remotehost
        self.send_request_owner(remotehost, table, rid, "update",tuples)
        logging.debug("[obm]: Remote update request.")
            
    def select_remote(self,table,admid,rid):
        remotehost = self.gethost(table,admid)
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        if self.location[table][rid] == self.myhost:
            self.setowner(table,rid,None,remotehost)
            
        resp = self.send_request_owner(remotehost,table,rid,"select")
        logging.debug("[obm]: Response from select: " + str(resp))
        self.tables[table][rid] = json.loads(resp)  
        return self.tables[table][rid]
            
    def select_diff_index(self,table,value,idxname):
        if idxname in self.indexes[table]:
            rids = self.indexes[table][idxname][value]
            result = []
            for rid in rids:
                result.append(self.select(table,rid))
            return result
        else:
            logging.error("[obm]: Index not created! Please create index first.")
            return False

    def gethost(self,table,admid):
        cmd = "select host from " + table + "_reg where `admid` = '" + admid + "'"
        return self.datacon.db.execute_one(cmd)['host']
    
    def getlocation(self,table,rid):
        cmd = "select host from " + table + "_obm where `rid` = '" + rid + "'"
        return self.datacon.db.execute_one(cmd)['host']
    
    def relocate(self,table,rid,newowner):
        if not rid in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        if self.location[table][rid] != self.myhost:
            self.location[table][rid] = self.getlocation(table,rid)
            # Update location just in case
            if self.location[table][rid] != self.myhost:
                logger.info("[obm]: Object is not here, sorry!")
                return "Failed"
        else:
            if not rid in self.tables[table]:
                cmd = "select * from " + table + " where " + self.ridnames[table] + " = " + rid
                # TODO: This will only return one result in every select! 
                self.tables[table][rid] = self.datacon.db.execute_one(cmd)
            if not self.tables[table][rid]:
                logging.warning("[obm/relocate]: Could not retrieve data")
            self.setowner(table,rid,self.tables[table][rid],newowner)

            return self.tables[table][rid]
                
    """
    request_relocate_to_local(self,table,rid): Requests that an object with rid is stored locally (i.e. same place as where
    the client is currently making requests to.
    """
    def request_relocate_to_local(self,table,rid):
        if not rid in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        self.send_request_owner(self.location[table][rid],table,rid,"relocate")
        
    """
    __send_request_owner(self,host,table,RID,name,update_value): Sends message to authoritative owner of object to update the current value of object with id=RID
    """    
    def send_request_owner(self,obj_location,table,RID,op,data=None,names=None):
        host,port = obj_location.split(':')
        if op == "update":
            cmd = "&op=update&tuples=" + urllib.quote(json.dumps(data))
        elif op == "select":
            cmd = "&op=select"
            if names:
                cmd += "&names=" + urllib.quote(json.dumps(names))
        elif op == "relocate":
            cmd = "&op=relocate&no=" + self.myhost
        elif op == "insert":
            cmd = "&op=insert&values=" + urllib.quote(json.dumps(data))
        # TODO: catch exception on timeout
        conn = httplib.HTTPConnection(host,port,timeout=4)
        logging.debug("[obm]: Sending request to " + obj_location)
        conn.request("GET", "/obm?rid="+str(RID)+"&tbl="+table+cmd)
        resp = conn.getresponse()
        if resp.status == 200:
            result = resp.read()
            return result
        else:
            logging.error("[obm]: Received a bad status from HTTP.")
