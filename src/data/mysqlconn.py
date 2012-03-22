'''
Created on March 21, 2012

@author: Arthur Valadares

mysqlconn.py: Used as an API between application layer and a MYSQL database. Uses python-mysqldb
'''

import MySQLdb as mdb
import sys

con = None
tables = {}
object_list = {}
# TODO: Set this to myip at some point!
myip = ""

class MySQLConnector():
    cur = None
        
    def open_connection(self,host,user,password,db):
        global con
        con = mdb.connect(host,user,password,db);
        self.cur = self.con.cursor()
                
    def execute(self,cmd):        
        self.cur.execute(cmd)
        return self.cur.fetchall()
    
    
    """
    select(): Return object (or one property of object). Requires finding authorative owner and requesting most recent status 
    """
    def select(self,table,name=None,RID):
        pass
    
    """
    update(): Updates property(ies) of an object. Requires finding authorative owner and requesting update of object.
    """
    def update(self,table,name,newvalue,RID):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["location"] != "LOCAL":
                    self.__send_update(tables[table][RID]["location"],table,property,newvalue,RID)
                else:
                    tables[table][RID][property] = newvalue
                return
            else:
                # TODO: Turn this SQL into: select * if location = none, else select * and set location to my IP
                rows = self.execute("SELECT * from %s WHERE RID = %s" ,(table,RID))
                if (rows["location"] != myip):
                    self.__send_update(rows["location"],table,property,newvalue,RID)
                else:
                    return
              
    """
    create(): Attempts to create a new item in the database and becomes the authorative owner of object
    """  
    def create(self,table,name,newvalue,RID):
        pass
    
    """
    delete(): Attempts to delete an new item in the database. Requires informing authorative owner (if one exists)
    and then deleting the object in the database
    """
    def delete(self,table,name,newvalue,RID):
        pass
        

    """
    __send_update(): Sends message to authorative owner of object to update the current value of object with id=RID
    """    
    def __send_update(self,host,table,name,newvalue,RID):
        pass

    """
    __send_select(): Sends message to authorative owner of object to retrieve all or just a property of an object with id=RID
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