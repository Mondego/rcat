'''
Created on March 21, 2012

@author: Arthur Valadares

mysqlconn.py: Used as an API between application layer and a MYSQL database. Uses python-mysqldb
'''

import MySQLdb as mdb
import sys
import itertools

conns = []
cursors = []
tables = {}
object_list = {}
# TODO: Set this to myip at some point!
myip = ""


class MySQLConnector():
    @ property
    def cur(self):
        global cursors
        return cursors.next()
        
    def open_connections(self,host,user,password,db,poolsize=None):
        global conns
        global cursors
        
        curs = []

        # Default connection pool = 10
        if not poolsize:
            poolsize = 10
            
        for i in range(poolsize):
            con = mdb.connect(host,user,password,db)
            conns.append(con);
            curs.append(con.cursor())
        cursors = itertools.cycle(curs)
                
    def execute(self,cmd):        
        self.cur.execute(cmd)
        return self.cur.fetchall()
    
    
    """
    select(): Return object (or one property of object). Requires finding authoritative owner and requesting most recent status 
    """
    def select(self,table,name=None,RID):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["location"] != "LOCAL":
                    self.__send_select(tables[table][RID]["location"],table,name,RID) 
                else:
                    if name:
                        return tables[table][RID][name]
                    else:
                        return tables[table][RID]
            else:
                # TODO: Turn this SQL into: select * if location = none, else select * and set location to my IP
                rows = self.execute("SELECT * from %s WHERE RID = %s" ,(table,RID))
                if (rows["location"] != myip):
                    self.__select(rows["location"],table,name,RID)
                    tables[table][RID] = rows
                else:
                    tables[table][RID] = rows
                    return rows
        else:
            return False
    
    """
    update(): Updates property(ies) of an object. Requires finding authoritative owner and requesting update of object.
    """
    def update(self,table,name,newvalue,RID):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["location"] != "LOCAL":
                    self.__send_update(tables[table][RID]["location"],table,name,newvalue,RID)
                else:
                    tables[table][RID][name] = newvalue
                return True
            else:
                # TODO: Turn this SQL into: select * if location = none, else select * and set location to my IP
                rows = self.execute("SELECT * from %s WHERE RID = %s" ,(table,RID))
                if (rows["location"] != myip):
                    self.__send_update(rows["location"],table,name,newvalue,RID)
                    
                else:
                    tables[table][RID] = rows
                    return True
        else:
            return False
              
    """
    create(): Attempts to create a new item in the database and becomes the authoritative owner of object.
    Input: List of values based on column order. Retrieve column order if desired with get_columns()
    """  
    def create(self,table,values,RID):
        if table in tables:
            if RID in tables[table]:
                self.execute("INSERT INTO %s VALUES(" + ','.join([`val` for val in values]) + ")" ,(table))
                cols = self.get_columns()
                newobj = {}
                for col,val in cols,values:
                    newobj[col] = val
                newobj["location"] = "LOCAL"
                tables[table][RID] = newobj
            else:
                return False
        else:
            return False
    
    """
    delete(): Attempts to delete an new item in the database. Requires informing authoritative owner (if one exists)
    and then deleting the object in the database
    """
    def delete(self,table,name,newvalue,RID):
        pass
        
    def get_columns(self,table):
        pass

    """
    __send_update(): Sends message to authoritative owner of object to update the current value of object with id=RID
    """    
    def __send_update(self,host,table,name,newvalue,RID):
        pass

    """
    __send_select(): Sends message to authoritative owner of object to retrieve all or just a property of an object with id=RID
    """
    def __send_select(self,host,table,name=None,RID):
        pass
    
if __name__=="__main__":
    con = None
    try:
    
        con = mdb.connect('opensim.ics.uci.edu', 'rcat', 
            'isnotamused', 'rcat');
    
        cur = con.cursor()
        cur.execute("SELECT VERSION()")
    
        data = cur.fetchone()
        
        print "Database version : %s " % data
    
    except:
        sys.exit(1)
        
    finally:    
            
        if con:    
            con.close()