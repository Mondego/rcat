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


conns = []
cursors = None

#datacon: Parent data connector
datacon = None

logger = logging.getLogger()

class MySQLConnector():
    tables_meta = {}
    db_updates = {}
    db_inserts = {}
    db = None
    # persist_timer: Interval where all updates are pushed to the database/persistent media.    
    persist_timer = None

    def __init__(self, dataconnector, persist_timer=3):
        global datacon
        self.persist_timer = persist_timer
        datacon = dataconnector
        logger.debug("[mysqlconn]: Starting MySQL Connector.")

    @ property
    def cur(self):
        global cursors
        return cursors.next()
        
    def open_connections(self, host, user, password, db, poolsize=None):
        # pt: persist timer
        global conns
        global cursors
        global ps_socket


        curs = []

        self.db = db
        # Default connection pool = 10
        if not poolsize:
            poolsize = 10
            
        for _ in range(poolsize):
            con = mdb.connect(host, user, password, db)
            conns.append(con);
            curs.append(con.cursor(mdb.cursors.DictCursor))
        cursors = itertools.cycle(curs)
        dtd = Timer(5.0, self.__dump_to_database__,[self.persist_timer])
        dtd.daemon = True
        dtd.start()
        
        ka = Timer(18000.0, self.keepalive)
        ka.daemon = True
        ka.start()
        
    def keepalive(self):
        logger.debug("[mysqlconn]: Keeping connection alive..")
        cur = self.cur
        cur.execute("show tables")
        firstcur = cur
        cur = self.cur
        while(cur != firstcur):
            cur.execute("show tables")
            cur = self.cur
        logger.debug("[mysqlconn]: All cursors updated.")
        ka = Timer(18000.0, self.keepalive)
        ka.daemon = True
        ka.start()
        
        
    def execute(self, cmd):
        cur = self.cur
        cur.execute(cmd)
        cur.connection.commit()
        res = cur.fetchall()
        return res
    
    def execute_one(self, cmd):
        cur = self.cur
        cur.execute(cmd)
        cur.connection.commit()
        res = cur.fetchone()
        return res
    
    def count(self, table):
        cur = self.cur
        cur.execute("select count(*) from " + table)
        res = cur.fetchone()
        return int(res['count(*)'])


    # TODO: Make this create based on arguments, not on entire SQL command
    def create_table(self, table, cmd, ridname):
        self.execute(cmd)
        self.retrieve_table_meta(table, ridname)
    
    def retrieve_table_meta(self, table, ridname, cols=None):
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
    def retrieve_column_names(self, table):
        metadata = self.execute("SHOW COLUMNS FROM " + table)
        fields = {}
        i = 0
        for tup in metadata:
            fields[tup['Field']] = i
            i += 1 
        return metadata, fields

    """
    __retrieve_object_from_db(self,table,RID):
    """
    def retrieve_object_from_db(self, table, RID):
        cur = self.cur
        try:
            rid_name = self.tables_meta[table]["ridname"]
            mystr = "SELECT * from %s WHERE `%s` = '%s'" % (table, rid_name, RID)
            cur.execute(mystr)
            return cur.fetchone()
        except mdb.cursors.Error, e:
            logger.error(e)
            return False
        
    def retrieve_multiple_from_db(self, table, param, param_name):
        cur = self.cur
        try:
            mystr = "SELECT * from %s WHERE `%s` = '%s'" % (table, param_name, param)
            cur.execute(mystr)
            return cur.fetchall()
        except mdb.cursors.Error, e:
            logger.error(e)
            return False
        
    """
    __dump_to_database__: Dumps updated locally owned objects to database
    """
    def __dump_to_database__(self, persist_timer):
        while(1):
            cur = self.cur
            for table in self.tables_meta.keys():
                if self.db_updates[table]:
                    loc_update = deepcopy(self.db_updates[table])
                    self.db_updates[table].clear()
                    while loc_update:
                        rid, row = loc_update.popitem()
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

            time.sleep(persist_timer)
    

    """
    select(self,table,name=None,RID): Return object (or one property of object). Requires finding authoritative owner and requesting most recent status 
    """
    def select(self, table, RID, names=None):
        return self.retrieve_object_from_db(table, RID)
    
    def delete(self, table, RID):
        cur = self.cur
        try:
            mystr = "DELETE from %s WHERE `%s` = '%s'" % (table, self.tables_meta[table]["ridname"], RID)
            cur.execute(mystr)
            cur.connection.commit()
            return True
        except mdb.cursors.Error, e:
            logger.error(e)
            return False

    # schedules an update to be pushed to the database at next iteration. 
    # Takes in the table name, the primary key (rid), and a dictionary of tuples (property,newvalue).
    # e.g. schedule_update("people","SSN",{"age":12,"name":"john"}]
    def schedule_update(self, table, rid, data):
        logger.debug("[mysqlconn]: Scheduling an update for " + table + ". Data is :" + str(data))
        self.db_updates[table][rid] = data
        return True

    def immediate_update(self,table,rid,obj):
        cur = self.cur
        try:
            mystr = ("UPDATE %s SET " % table)
            mystr += ','.join([' = '.join([`str(key)`.replace("'", "`"), `str(val)`]) for key, val in obj.items()])
            mystr += " WHERE %s = '%s'" % (str(self.tables_meta[table]["ridname"]), rid)
            logger.debug("[mysqlconn]: Dumping to database: " + mystr)
            cur.execute(mystr)
            cur.connection.commit()
            return True
        except mdb.cursors.Error, e:
            logger.error(e)
            return False
        
    def insert_batch(self, table, list_values):
        mystr = ''
        try:
            mystr = ("INSERT INTO %s VALUES(" % table) + ',('.join([','.join([`str(val)` for val in values]) + ")" for values in list_values])
            cur = self.cur
            cur.execute(mystr)
            cur.connection.commit()
                # Auto-increment?
        except mdb.cursors.Error, e:
                logger.error(e)
                return False;
        
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

    def clear_table(self, table):
        self.execute("delete * from " + table)

    def insert_dict_to_list(self, table, dic):
        cols = self.tables_meta[table]["columns"]
        insert_list = [None] * len(cols)
        for item in cols.keys():
            insert_list[cols[item]] = dic[item]
        return insert_list
        
        
