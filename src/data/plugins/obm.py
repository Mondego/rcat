'''
Created on May 18, 2012

@author: arthur
'''
import json
import tornado.web
import urllib
import httplib
import logging

obm = None
logger = logging.getLogger()

class OBMHandler(tornado.web.RequestHandler):
    def initialize(self, datacon):
        global pubsubs
        pubsubs = {}
    
    def get(self):
        # Constraint! RID is always an INT
        rid = int(self.get_argument("rid",None))
        tbl = self.get_argument("tbl",None)
        op = self.get_argument("op",None)
        if op == "update":
            tuples = json.loads(self.get_argument("tuples"),None)
            obm.update(tbl,tuples,rid)
            self.write("OK")
        elif op == "select":
            jnames = None
            names = self.get_argument("names",None)
            if names:
                jnames = json.loads(names)
            obj = obm.select(tbl,rid,jnames)
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
        self.obm = self
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
        cmd = "create table if not exists " + table + "_obm(rid " + rid_type + " not null,host varchar(255) not null, primary key(rid))"
        self.datacon.db.execute(cmd)
        cmd = "create table if not exists " + table + "_reg(admid varchar(255) not null,host varchar(255) not null, primary key(admid))"
        self.datacon.db.execute(cmd)
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
    
    def create_index(self,table,idxname):
        self.indexes[table][idxname] = {}
            
    def setowner(self,table,rid,values,owner=None):
        if not owner:
            owner = self.myhost
        else:
            owner = self.gethost(table,owner)
        try:
            if not self.tables[table]:
                self.tables[table] = {}
            self.datacon.db.insert(table+"_obm",[rid,owner])
            self.tables[table][rid] = values
            self.location[table][rid] = owner
        except Exception, e:
            logger.exception("[obm]: Failed to set owner in database.")
            return False
        
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
        
        self.setowner(table,rid,values)
        
        # Updates secondary indexes
        for idx in self.indexes[table].keys():
            value = values[self.columns[table][idx]]
            if value in self.indexes[table][idx]:
                self.indexes[table][idx][value].append(rid)
            else:
                self.indexes[table][idx][value] = [rid]
            
    
    def select(self,table,rid):
        # If I don't know where it is, find it in the database
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        
        if self.location[table][rid] == self.myhost:
            # If I own it but I don't have it in memory, fetch from database
            if not rid in self.tables[table]:
                cmd = "select * from " + table + " where " + self.ridnames[table] + " = " + rid
                # TODO: This will only return one result in every select! 
                self.tables[table][rid] = self.datacon.db.execute_one(cmd)
            return self.tables[table][rid]
        else:
            # If I don't own it, ask the owner to select for me
            self.send_request_owner(self.location[table][rid],table,rid,"select")
            
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
        return self.datacon.db.execute_one(cmd)
    
    def getlocation(self,table,rid):
        cmd = "select host from " + table + "_obm where `rid` = '" + rid + "'"
        return self.datacon.db.execute_one(cmd)
    
    def update(self,table,rid,update_tuples):
        # If I don't know where it is, find it in the database
        if rid not in self.location[table]:
            self.location[table][rid] = self.getlocation(table,rid)
        
        if self.location[table][rid] == self.myhost:
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
        else:
            # If I don't own it, ask the owner to select for me
            self.send_request_owner(self.location[table][rid],table,rid,"select")
        
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
    def send_request_owner(self,obj_location,table,RID,op,names=None,update_tuples=None):
        host,port = obj_location.split(':')
        if op == "update":
            cmd = "&op=update&tuples=" + urllib.quote(json.dumps(update_tuples))
        elif op == "select":
            cmd = "&op=select"
            if names:
                cmd += "&names=" + urllib.quote(json.dumps(names))
        elif op == "relocate":
            cmd = "&op=relocate&no=" + self.myhost
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
