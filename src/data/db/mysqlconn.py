'''
Created on March 21, 2012

@author: Arthur Valadares

mysqlconn.py: Used as an API between application layer and a MYSQL database. Uses python-mysqldb
'''

import MySQLdb as mdb
import itertools
import json
import logging
from copy import deepcopy

obm = None
conns = []
cursors = []
tables = {}
object_list = {}
logger = logging.getLogger()
mysqlconn = None
pubsubs = None
location = {}
db_updates = {}
db_inserts = {}

class MySQLConnector():
    def __init__(self,datacon):
        global mysqlconn
        global obm
        self.mylocation = datacon.mylocation
        logger.debug("[mysqlconn]: Starting MySQL Connector. My location is " + self.mylocation)
        mysqlconn = self

    @ property
    def cur(self):
        global cursors
        return cursors.next()
        
    def open_connections(self,host,user,password,db,poolsize=None):
        global conns
        global cursors
        global ps_socket
        curs = []

        # Default connection pool = 10
        if not poolsize:
            poolsize = 10
            
        for _ in range(poolsize):
            con = mdb.connect(host,user,password,db)
            conns.append(con);
            curs.append(con.cursor(mdb.cursors.DictCursor))
        cursors = itertools.cycle(curs)
        
    def execute(self,cmd):
        cur = self.cur
        cur.execute(cmd)
        cur.connection.commit()
        return cur.fetchall()
    
    
    """
    __retrieve_column_names(self,table): Retrieves column names from the database
    """
    def retrieve_column_names(self,table):
        metadata = self.execute("SHOW COLUMNS FROM " + table)
        fields = {}
        i = 0
        for tup in metadata:
            fields[tup['Field']] = i
            i+=1 
        return metadata,fields

    """
    __retrieve_object_from_db(self,table,RID,name=None,update_values=None):
    update_value: tuple with (old_value,new_value)
    """
    def retrieve_object_from_db(self,table,RID,names=None,update_values=None):
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
            if (row["__location__"] != self.mylocation):
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