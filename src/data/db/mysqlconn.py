'''
Created on March 21, 2012

@author: Arthur Valadares

mysqlconn.py: Used as an API between application layer and a MYSQL database. Uses python-mysqldb
'''

from copy import deepcopy
import MySQLdb as mdb
import itertools
import logging
import time
from threading import Timer


obm = None
conns = []
cursors = None
#tables = {}
object_list = {}
logger = logging.getLogger()
mysqlconn = None
#pubsubs = {}

class MySQLConnector():
    tables_meta = {}
    db_updates = {}
    db_inserts = {}

    def __init__(self,datacon):
        global mysqlconn
        global obm
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
        curs = []

        # Default connection pool = 10
        if not poolsize:
            poolsize = 10
            
        for _ in range(poolsize):
            con = mdb.connect(host,user,password,db)
            conns.append(con);
            curs.append(con.cursor(mdb.cursors.DictCursor))
        cursors = itertools.cycle(curs)
        Timer(5.0, self.__dump_to_database__).start()
        
    def execute(self,cmd):
        cur = self.cur
        cur.execute(cmd)
        cur.connection.commit()
        return cur.fetchall()
    
    def execute_one(self,cmd):
        cur = self.cur
        cur.execute(cmd)
        cur.connection.commit()
        return cur.fetchone()
    
    
    def retrieve_table_meta(self, table, ridname,cols=None):
        self.tables_meta[table] = {}
        self.tables_meta[table]["ridname"] = ridname
        
        self.db_updates[table] = {}
        self.db_inserts[table] = {}
        if (cols):
            self.tables_meta[table]["columns"] = cols
        else:
            metadata, fields = self.retrieve_column_names(table)
            self.tables_meta[table]["metadata"] = metadata
            self.tables_meta[table]["columns"] = fields
    
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
    def retrieve_object_from_db(self,table,RID):
        cur = self.cur
        try:
            rid_name = self.tables_meta[table]["ridname"]
            mystr = "SELECT * from %s WHERE `%s` = '%s'" % (table,rid_name,RID)
            cur.execute(mystr)
            return cur.fetchone()
        except mdb.cursors.Error,e:
            logger.error(e)
            return False
        
    def retrieve_multiple_from_db(self,table,param,param_name):
        cur = self.cur
        try:
            mystr = "SELECT * from %s WHERE `%s` = '%s'" % (table,param_name,param)
            cur.execute(mystr)
            return cur.fetchall()
        except mdb.cursors.Error,e:
            logger.error(e)
            return False
        
    """
    __dump_to_database__: Dumps updated locally owned objects to database
    """
    def __dump_to_database__(self):
        while(1):
            cur = self.cur
            for table in self.tables_meta.keys():
                if self.db_updates[table]:
                    loc_update = deepcopy(self.db_updates[table])
                    self.db_updates[table].clear()
                    while loc_update:
                        rid,row = loc_update.popitem()
                        try:
                            mystr = ("UPDATE %s SET " % table)
                            mystr += ','.join([' = '.join([`str(key)`.replace("'", "`"), `str(val)`]) for key, val in row.items()])
                            mystr += " WHERE %s = '%s'" % (str(self.tables_meta[table]["ridname"]), rid)
                            logger.debug("[mysqlconn]: Dumping to database: " + mystr)
                            cur.execute(mystr)
                            cur.connection.commit()
                        except mdb.cursors.Error, e:
                            print e
                    # perform the inserts
                    loc_inserts = self.db_inserts[table]
                    self.db_inserts[table] = []
                    for mystr in loc_inserts:
                        try:
                            logger.debug("[mysqlconn]: Inserting new values to database: " + mystr)
                            cur.execute(mystr)
                            cur.connection.commit()
                        except mdb.cursors.Error, e:
                            print e

            time.sleep(5)
    

    """
    select(self,table,name=None,RID): Return object (or one property of object). Requires finding authoritative owner and requesting most recent status 
    """
    def select(self, table, RID, names=None):
        return self.retrieve_object_from_db(table, RID, names)
    
    def delete(self,table,RID):
        cur = self.cur
        try:
            mystr = "DELETE from %s WHERE `%s` = '%s'" % (table,self.tables_meta[table]["ridname"],RID)
            cur.execute(mystr)
            cur.connection.commit()
            return True
        except mdb.cursors.Error,e:
            logger.error(e)
            return False

    def schedule_update(self,table,rid,data):
        logger.debug("[mysqlconn]: Scheduling an update for " + table + ". Data is :" + str(data))
        self.db_updates[table][rid] = data
        return True

    """
    insert(self,table,values,RID): Attempts to create a new item in the database and becomes the authoritative owner of object.
    Input: List of values based on column order. Retrieve column order if desired with get_columns()
    """
    def insert(self, table, values, autoinc=False):
        try:
            cur = self.cur
            mystr = ("INSERT INTO %s VALUES(" % table) + ','.join([`str(val)` for val in values]) + ")"
            logger.debug(mystr)
            cur.execute(mystr)
            cur.connection.commit()
            # Auto-increment?
            if autoinc:
                # Probably wrong!
                cur.execute("SELECT LAST_INSERT_ID();")
                result = cur.fetchone()
                RID = result['LAST_INSERT_ID()']
                return RID
        except mdb.cursors.Error, e:
                logger.error(e)
                return False;
