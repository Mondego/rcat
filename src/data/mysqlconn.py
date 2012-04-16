'''
Created on March 21, 2012

@author: Arthur Valadares

mysqlconn.py: Used as an API between application layer and a MYSQL database. Uses python-mysqldb
'''

from threading import Timer
import MySQLdb as mdb
import common.helper as helper
import itertools
import logging
import sys
import time
import tornado.web
import json
import httplib
import urllib
import SocketServer
import socket
import pubsub

conns = []
cursors = []
tables = {}
object_list = {}
logger = logging.getLogger()
myip = ''
mysqlconn = None
ps_socket = None
pubsubs = None

class ObjectManager(tornado.web.RequestHandler):
    def get(self):
        if self.get_argument("subscribe",None):
            tbl = self.get_argument("tbl",None)
            interests = json.loads(self.get_argument("interests",None))
            ip =  self.get_argument("ip",None)
            port = self.get_argument("port",None)
            location = (ip,port)
            
            pubsubs[tbl].add_subscriber(location,interests) 
            
        else:            
            rid = self.get_argument("rid",None)
            tbl = self.get_argument("tbl",None)
            op = self.get_argument("op",None)
            if op == "update":
                tuples = json.loads(self.get_argument("tuples"),None)   
                mysqlconn.update(tbl,tuples,rid)
                self.write("OK")
            else:
                names = json.loads(self.get_argument("names",None))
                obj = mysqlconn.select(tbl,rid,names)
                self.write(str(obj))

class MySQLConnector():
    def __init__(self,ip=None):
        global myip
        global mysqlconn
        if not ip:
            ip = helper.get_ip_address('eth0')
        myip = ip
        logger.debug("[mysqlconn]: Starting MySQL Connector.")
        mysqlconn = self

    @ property
    def cur(self):
        global cursors
        return cursors.next()
        
    def open_connections(self,host,user,password,db,poolsize=None):
        global conns
        global cursors
        global ps_socket
        global pubsub_manager
        
        curs = []

        # Default connection pool = 10
        if not poolsize:
            poolsize = 10
            
        for _ in range(poolsize):
            con = mdb.connect(host,user,password,db)
            conns.append(con);
            curs.append(con.cursor(mdb.cursors.DictCursor))
        cursors = itertools.cycle(curs)
        
        """
        Start Publish-Subscribe UDP socket to receive data subscribed to 
        """
        HOST, PORT = myip, 9999
        server = SocketServer.UDPServer((HOST, PORT), pubsub.PubSubUpdateHandler)
        server.serve_forever()
        
        ps_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        """
        Start the thread that dumps to database
        """
        Timer(5.0,self.__dump_to_database__).start()
                
    def execute(self,cmd):
        cur = self.cur
        cur.execute(cmd)
        cur.connection.commit()
        return cur.fetchall()
    
    
    """
    TODO: Make this work! 
    """
    def __dump_to_database__(self):
        while(1):
            cur = self.cur 
            #logger.debug("[mysqlconn]: Dumping to database.")
            for tblnames,tblvalues in tables.items():
                for itemname,itemvalues in tblvalues.items():
                    if not itemname.startswith("__"):
                        if itemvalues["__location__"] == myip:
                            try:                                
                                mystr = ("UPDATE %s SET " % tblnames) + ','.join([' = '.join([`key`.replace("'","`"),`val`]) for key,val in itemvalues.items()]) + " WHERE %s = %s" % (tblvalues["__ridname__"],itemname)
                                print mystr
                                cur.execute(mystr)
                                cur.connection.commit()
                            except mdb.cursors.Error,e:
                                print e
            time.sleep(5)
                
    
    """
    create_table(self,name,cols=None,null=None,defaults=None): Creates a table with specified column names and data types
    """
    def create_table(self,name,rid_name,cols=None,null=None,defaults=None):
        # TODO: This is freaking hard! I will think about it later. For now, allow clients to inform table to be stored in memory
        # cmd= "CREATE TABLE " + name + " (" + ','.join([colname+colnull+coldef for colname,colnull,coldef in cols,null,defaults]) 
        tables[name] = {}
        tables[name]["__ridname__"] = rid_name
        pubsubs[name] = pubsub.PubSubUpdateSender(name)
        if (cols):
            tables[name]["__columns__"] = cols
        else:
            self.__retrieve_column_names(name)
            
    """
    select(self,table,name=None,RID): Return object (or one property of object). Requires finding authoritative owner and requesting most recent status 
    """
    def select(self,table,RID, names=None):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["__location__"] != myip:
                    self.__send_select_owner(tables[table][RID]["__location__"],table,names,RID) 
                else:
                    if names:
                        newdic = {}
                        for name in names:
                            newdic[name] = tables[table][RID][name]
                        return newdic
                    else:
                        row = tables[table][RID]
                        return row
            else:
                return self.__retrieve_object_from_db(table,RID,name,None)
        else:
            return False
    
    """
    update(self,table,update_tuples,RID): Updates property(ies) of an object. Requires finding authoritative owner and requesting update of object.
    update_tuples: List or tuple of tuples (column name, new value)
    """
    def update(self,table,update_tuples,RID):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["__location__"] != myip:
                    self.__send_update_owner(tables[table][RID]["__location__"],table,update_tuples,RID)
                else:
                    # TODO: Remove unneeded headers from dictionary. For now, makes our lives easier
                    tuples_dic = {}
                    for item in update_tuples:
                        tables[table][RID][item[0]] = item[1]
                        tuples_dic[item[0]] = item[1]
                    pubsubs[table].send(RID,tuples_dic)
                        
                return True
            else:
                return self.__retrieve_object_from_db(table,RID,None,update_tuples)
        else:
            return False
              
    """
    insert(self,table,values,RID): Attempts to create a new item in the database and becomes the authoritative owner of object.
    Input: List of values based on column order. Retrieve column order if desired with get_columns()
    """  
    def insert(self,table,values,RID):
        cur = self.cur
        # metadata: myip stores the IP where the authoritative object is
        values.append(myip)
        if table in tables:
            if RID not in tables[table]:
                try:
                    mystr = ("INSERT INTO %s VALUES(" % table) + ','.join([`val` for val in values]) + ")"
                    cur.execute(mystr)
                    cur.connection.commit()
                    newobj = {}
                    for name,idx in tables[table]["__columns__"].items():
                        newobj[name] = values[idx] 
                    tables[table][RID] = newobj
                except mdb.cursors.Error,e:
                    logger.error(e)
                    return False;
            else:
                return False
        else:
            return False
    
    """
    delete(self,table,name,newvalue,RID): Attempts to delete an new item in the database. Requires informing authoritative owner (if one exists)
    and then deleting the object in the database
    """
    def delete(self,table,name,newvalue,RID):
        pass
        
    """
    get_columns(self,table): Retrieve list of column names from memory
    """
    def get_columns(self,table):
        return tables[table]["__columns__"]
    
    """
    __retrieve_column_names(self,table): Retrieves column names from the database
    """
    def __retrieve_column_names(self,table):
        metadata = self.execute("SHOW COLUMNS FROM " + table)
        fields = {}
        i = 0
        for tup in metadata:
            fields[tup['Field']] = i
            i+=1 
        tables[table]["__metadata__"] = metadata
        tables[table]["__columns__"] = fields

    """
    __retrieve_object_from_db(self,table,RID,name=None,update_values=None): -------
    update_value: tuple with (old_value,new_value)
    """
    def __retrieve_object_from_db(self,table,RID,name=None,update_values=None):
        cur = self.cur
        try:
            rid_name = tables[table]["__ridname__"]
            cur.execute("SELECT * from %s WHERE %s = %s" ,(table,rid_name,RID))
            row = cur.fetchone()
            if not row["__location__"]:
                cur.execute("UPDATE %s SET location = '%s' WHERE %s = %s", (table,myip,rid_name,RID))
                cur.commit() 
                return row
            if (row["__location__"] != myip):
                if update_values:
                    self.__send_request_owner(row["__location__"],table,RID,None,update_values)
                else:
                    self.__send_request_owner(row["__location__"],table,RID,name)
                tables[table][RID] = {}
                tables[table][RID]["__location__"] = row["__location__"]
            else:
                tables[table][RID] = row.copy()
                return row
        except:
            return False
        
    """
    __send_request_owner(self,host,table,RID,name,update_value): Sends message to authoritative owner of object to update the current value of object with id=RID
    """    
    def __send_request_owner(self,host,table,RID,names=None,update_tuples=None):
        if update_tuples:
            cmd = "?op=update&tuples=" + urllib.quote(json.dumps(update_tuples))
        else:
            cmd = "?op=select"
            if names:
                cmd += "&names=" + urllib.quote(json.dumps(names))
        conn = httplib.HTTPConnection(host)
        conn.request("GET", "/obm?rid="+RID+"&tbl="+table+cmd)
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
            return resp.read()
    
if __name__=="__main__":
    HOST, PORT = "localhost", 7777
    server = SocketServer.UDPServer((HOST, PORT), pubsub.PubSubUpdateHandler)
    server.serve_forever()
    """
    con = None
    try:
    
        con = mdb.connect('opensim.ics.uci.edu', 'rcat', 
            'isnotamused', 'rcat');
    
        cur = con.cursor(mdb.cursors.DictCursor)
        #cur.execute("INSERT INTO users VALUES(123456789,0,0,0,0)")
        cur.execute("select * from users")
                    
        rows = cur.fetchall()
        cur.connection.commit()
        #print data
        #print data["name"]
        for row in rows:
            print row["name"]
        print rows
        print cur.description
        
    except mdb.connections.Error, e:
        con.rollback()
        print "Error %d: %s" % (e.args[0],e.args[1])
        sys.exit(1)
        
    finally:    
            
        if con:    
            con.close()
    """