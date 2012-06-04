from data.dataconn import Mapper
import MySQLdb as mdb
import json
import logging
import time
from threading import Timer

from collections import defaultdict
from copy import deepcopy

import data.plugins.pubsub as pubsub

obm = None
tables = {}
object_list = {}
logger = logging.getLogger()
mylocation = ''
mysqlconn = None
pubsubs = {}
location = {}
db_updates = {}
db_inserts = {}

class ChatManager(Mapper):
    def __init__(self,db=None):
        global mylocation
        """
        Start the thread that dumps to database
        """
        self.db = db
        mylocation = db.mylocation
        self.mylocation = mylocation
        self.location = location
        self.tables = tables
        self.pubsubs = pubsubs
        Timer(5.0,self.__dump_to_database__).start()
    
    @property
    def name(self):
        return "ChatManager"
    
    """
    __dump_to_database__: Dumps updated locally owned objects to database
    """
    def __dump_to_database__(self):
        while(1):
            cur = self.db.cur
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
            metadata,fields = self.db.retrieve_column_names(name)
            tables[name]["__metadata__"] = metadata
            tables[name]["__columns__"] = fields
            

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
                result = self.db.retrieve_object_from_db(table,RID,names,None)
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
                return self.db.retrieve_object_from_db(table,RID,None,update_tuples)
        else:
            return False
              
    """
    insert(self,table,values,RID): Attempts to create a new item in the database and becomes the authoritative owner of object.
    Input: List of values based on column order. Retrieve column order if desired with get_columns()
    """  
    def insert(self,table,values,RID):
        cur = self.db.cur
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
    
