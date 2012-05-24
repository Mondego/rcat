'''
Created on March 21, 2012

@author: Arthur Valadares

mysqlconn.py: Used as an API between application layer and a MYSQL database. Uses python-mysqldb
'''

from threading import Timer
import MySQLdb as mdb
import SocketServer
import itertools
import json
import logging
import time
from collections import defaultdict
from copy import deepcopy

import data.plugins.obm
import data.plugins.pubsub as pubsub
from data.plugins.obm import ObjectManager

obm = None
conns = []
cursors = []
tables = {}
object_list = {}
logger = logging.getLogger()
mylocation = ''
mysqlconn = None
pubsubs = None
location = {}
db_updates = {}
db_inserts = {}

class MySQLConnector():
    def __init__(self,myip,myport,handlers=None,options=None):
        global mylocation
        global mysqlconn
        global obm
        mylocation = myip + ':' + myport
        logger.debug("[mysqlconn]: Starting MySQL Connector. My location is " + mylocation)
        mysqlconn = self
        
        if options:
            # Set new handlers to main application
            if "plugins" in options:
                for plg in options["plugins"]:
                    if plg == "obm":
                        obm = ObjectManager(mylocation,tables,location)
                        handlers.append((r"/obm", data.plugins.obm.ObjectManager, dict(conn=self,pubsub_list=pubsubs)))
                    elif plg == "pubsub":
                        """
                        Start Publish-Subscribe UDP socket to receive data subscribed to 
                        """
                        HOST, PORT = myip,int(myport) + 1
                        server = SocketServer.UDPServer((HOST, PORT), data.plugins.pubsub.PubSubUpdateHandler)
                        Timer(5.0,server.serve_forever).start()

    @ property
    def cur(self):
        global cursors
        return cursors.next()
        
    def open_connections(self,host,user,password,db,poolsize=None):
        global conns
        global cursors
        global ps_socket
        global pubsubs
        curs = []
        pubsubs = {}

        # Default connection pool = 10
        if not poolsize:
            poolsize = 10
            
        for _ in range(poolsize):
            con = mdb.connect(host,user,password,db)
            conns.append(con);
            curs.append(con.cursor(mdb.cursors.DictCursor))
        cursors = itertools.cycle(curs)
        
        
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
    __dump_to_database__: Dumps updated locally owned objects to database
    """
    def __dump_to_database__(self):
        while(1):
            cur = self.cur 
            for tblnames,tblvalues in tables.items():
                loc_update = deepcopy(db_updates[tblnames])
                db_updates[tblnames].clear()
                while loc_update:
                    rid = loc_update.pop()
                    itemvalues = tblvalues[rid]
                    if not str(rid).startswith("__"):
                        for row in itemvalues:
                            if location[tblnames][rid] == mylocation:
                                try:
                                    mystr = ("UPDATE %s SET " % tblnames) + ','.join([' = '.join([`key`.replace("'","`"),`str(val)`]) for key,val in row.items()]) + " WHERE %s = %s" % (tblvalues["__ridname__"],rid)
                                    logger.debug("[mysqlconn]: Dumping to database: " + mystr)
                                    cur.execute(mystr)
                                    cur.connection.commit()
                                except mdb.cursors.Error,e:
                                    print e
                # perform the inserts
                loc_inserts = db_inserts[tblnames]
                db_inserts[tblnames] = []
                for mystr in loc_inserts:
                    try:                    
                        logger.debug("[mysqlconn]: Inserting new values to database: " + mystr)
                        cur.execute(mystr)
                        cur.connection.commit()
                    except mdb.cursors.Error,e:
                        print e
    
            time.sleep(5)
    
    """
    create_table(self,name,cols=None,null=None,defaults=None): Creates a table with specified column names and data types
    """
    def create_table(self,name,rid_name,cols=None,opts=None):
        # TODO: This is freaking hard! I will think about it later. For now, allow clients to inform table to be stored in memory
        # cmd= "CREATE TABLE " + name + " (" + ','.join([colname+colnull+coldef for colname,colnull,coldef in cols,null,defaults])
        tables[name] = defaultdict(list)
        tables[name]["__ridname__"] = rid_name
        pubsubs[name] = pubsub.PubSubUpdateSender(name)
        location[name] = {}
        db_updates[name] = set()
        db_inserts[name] = []
        if (cols):
            tables[name]["__columns__"] = cols
        else:
            self.__retrieve_column_names(name)

    """
    select(self,table,name=None,RID): Return object (or one property of object). Requires finding authoritative owner and requesting most recent status 
    """
    def select(self,table,RID,names=None):
        result = None
        if table in tables:
            if RID in tables[table]:
                if location[table][RID] != mylocation:
                    jsonobj = obm.send_request_owner_request_owner(location[table][RID],table,RID,"select",names)
                    result = json.loads(jsonobj)
                    return result
                else:
                    if not names:
                        return deepcopy(tables[table][RID])
                    else:
                        result = []
                        for item in tables[table][RID]:
                            newobj = {}
                            for name in names:
                                newobj[name] = item[name]
                            result.append(newobj)
                    return result
            else:
                result = self.__retrieve_object_from_db(table,RID,names,None)
                return result 
        else:
            return False
    
    """
    update(self,table,update_tuples,RID): Updates property(ies) of an object. Requires finding authoritative owner and requesting update of object.
    update_tuples: List or tuple of tuples (column name, new value)
    """
    def update(self,table,update_tuples,RID,row=0):
        if table in tables:
            if RID in tables[table]:
                obm.send_request_owner(location[table][RID],table,RID,"update",None,update_tuples)
                # TODO: Remove unneeded headers from dictionary. For now, makes our lives easier
                tuples_dic = {}
                for item in update_tuples:
                    tables[table][RID][row][item[0]] = item[1]
                    tuples_dic[item[0]] = item[1]
                pubsubs[table].send(RID,tuples_dic)
                db_updates[table].add(RID)
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
        # metadata: mylocation stores the IP where the authoritative object is
        values.append(mylocation)
        if table in tables:
            newobj = {}
            logger.debug("[mysqlconn]: New object: " + str(values))
            logger.debug("[mysqlconn]: Columns in table: " + str(tables[table]["__columns__"].items()))
            for name,idx in tables[table]["__columns__"].items():
                if not str(name).startswith('__location'):
                    newobj[name] = values[idx]
            mystr = ("INSERT INTO %s VALUES(" % table) + ','.join([`str(val)` for val in values]) + ")"
            if RID not in tables[table]:
                try:
                    logger.debug(mystr)
                    cur.execute(mystr)
                    cur.connection.commit()
                except mdb.cursors.Error,e:
                    logger.error(e)
                    return False;
            else:
                db_inserts[table].append(mystr)
            location[table][RID] = mylocation
            tables[table][RID].append(newobj)
            pubsubs[table].send(RID,newobj)
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
    __retrieve_object_from_db(self,table,RID,name=None,update_values=None):
    update_value: tuple with (old_value,new_value)
    """
    def __retrieve_object_from_db(self,table,RID,names=None,update_values=None):
        cur = self.cur
        try:
            rid_name = tables[table]["__ridname__"]
            cur.execute("SELECT * from %s WHERE %s = %s".replace("'","`") % (table,rid_name,RID))
            allrows = cur.fetchall()
            
            if len (allrows) > 0:
                row = allrows[0]
            else:
                return False
            if not row["__location__"]:
                obm.set_object_owner(table,RID)
                return deepcopy(tables[table][RID])
            if (row["__location__"] != mylocation):
                cur.connection.commit()
                location[table][RID] = row["__location__"]
                if update_values:
                    op = "update"
                else:
                    op = "select"
                result = obm.send_request_owner(row["__location__"],table,RID,op,names,update_values)
                # True or false for update; object for select
                if not update_values:
                    if result:
                        tables[table][RID] = json.loads(result)
                        ret_copy = deepcopy(tables[table][RID])
                        return ret_copy
                    else:
                        logger.error("[mysqlconn]: Did not receive remote object")
                        return "ERROR"
                else:
                    return result
            else:
                # TODO: Delete location information from each row!
                tables[table][RID] = allrows
                return deepcopy(tables[table][RID])
        except mdb.cursors.Error,e:
            logger.error(e)
            return False
