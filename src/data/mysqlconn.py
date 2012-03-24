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
            curs.append(con.cursor(mdb.cursors.DictCursor))
        cursors = itertools.cycle(curs)
                
    def execute(self,cmd):
        cur = self.cur
        cur.execute(cmd)
        return cur.fetchall()
    
    
    """
    create_table(self,name,cols=None,null=None,defaults=None    ): Creates a table with specified column names and data types
    """
    def create_table(self,name,cols=None,null=None,defaults=None,rid_name=None):
        # TODO: This is freaking hard! I will think about it later. For now, allow clients to inform table to be stored in memory
        # cmd= "CREATE TABLE " + name + " (" + ','.join([colname+colnull+coldef for colname,colnull,coldef in cols,null,defaults]) 
        tables[name] = {}
        tables[name]["__ridname__"] = rid_name
        if (cols):
            tables[name]["__columns__"] = cols
        else:
            tables[name]["__columns__"] = self.__retrieve_column_names(name)
            
    """
    select(self,table,name=None,RID): Return object (or one property of object). Requires finding authoritative owner and requesting most recent status 
    """
    def select(self,table,RID, name=None):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["location"] != myip:
                    self.__send_select_owner(tables[table][RID]["location"],table,name,RID) 
                else:
                    if name:
                        return tables[table][RID][name]
                    else:
                        row = tables[table][RID]
                        del row["location"]
                        return row
            else:
                self.__retrieve_object_from_db(table,RID,name,None)
        else:
            return False
    
    """
    update(self,table,name,newvalue,RID): Updates property(ies) of an object. Requires finding authoritative owner and requesting update of object.
    """
    def update(self,table,update_tuples,RID):
        if table in tables:
            if RID in tables[table]:
                if tables[table][RID]["location"] != myip:
                    self.__send_update_owner(tables[table][RID]["location"],table,update_tuples,RID)
                else:
                    # TODO: Remove unneeded headers from dictionary. For now, makes our lives easier
                    #vec_index = tables[table]["__columns__"][name]
                    #(tables[table][RID]["values"])[vec_index] = newvalue
                    for item in update_tuples:
                        tables[table][RID][item[0]] = item[1]
                    
                return True
            else:
                self.__retrieve_object_from_db(table,RID,None,update_tuples)
        else:
            return False
              
    """
    create(self,table,values,RID): Attempts to create a new item in the database and becomes the authoritative owner of object.
    Input: List of values based on column order. Retrieve column order if desired with get_columns()
    """  
    def create(self,table,values,RID):
        cur = self.cur
        # metadata: myip stores the IP where the authoritative object is
        values.append(myip)
        if table in tables:
            if RID in tables[table]:
                try:
                    cur.execute("INSERT INTO %s VALUES(" + ','.join([`val` for val in values]) + ")" ,(table))
                    cur.connection.commit()
                    newobj = {}
                    x = 0
                    for name in tables[table]["__columns__"]:
                        newobj[name] = values[x] 
                        x += 1
                    tables[table][RID] = newobj
                except mdb.cursors.Error,e:
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
        metadata = cur.execute("SHOW COLUMNS FROM " + table)
        fields = {}
        i = 0
        for tup in metadata:
            fields[tup[0]] = i
            i+=1 
        tables[table]["__metadata__"] = metadata
        tables[table]["__columns__"] = fields

    """
    
    update_value: tuple with (old_value,new_value)
    """
    def __retrieve_object_from_db(self,table,RID,name=None,update_values=None):
        cur = self.cur
        try:
            rid_name = tables[table]["__ridname__"]
            cur.execute("SELECT * from %s WHERE %s = %s" ,(table,rid_name,RID))
            row = cur.fetchone()
            if not row["location"]:
                # TODO: Add code to insert me as the new owner 
                pass
            if (row["location"] != myip):
                if update_values:
                    self.__send_update_owner(row["location"],table,update_values,RID)
                else:
                    self.__send_select_owner(row["location"],table,RID,name)
                tables[table][RID] = {}
                tables[table][RID]["location"] = row["location"]
            else:
                tables[table][RID] = row
                del row["location"]
                return row
        except:
            return False
        
    """
    __send_update_owner(self,host,table,RID,name,update_value): Sends message to authoritative owner of object to update the current value of object with id=RID
    """    
    def __send_update_owner(self,host,table,update_tuples,RID):
        pass

    """
    __send_select_owner(self,host,table,name=None,RID): Sends message to authoritative owner of object to retrieve all or just a property of an object with id=RID
    """
    def __send_select_owner(self,host,table,RID,name=None):
        pass

    
if __name__=="__main__":
    con = None
    try:
    
        con = mdb.connect('opensim.ics.uci.edu', 'rcat', 
            'isnotamused', 'rcat');
    
        #cur = con.cursor()
        cur = con.cursor(mdb.cursors.DictCursor)
        #cur.execute("INSERT INTO users VALUES(123456789,0,0,0,0)")
        cur.execute("select * from users")
                    
        #data = cur.fetchone()
        rows = cur.fetchall()
        cur.connection.commit()
        #print data
        #print data["name"]
        for row in rows:
            print row["name"]
        print rows
        print cur.description
        
        
        #print "Database version : %s " % data
    
    except mdb.connections.Error, e:
        con.rollback()
        print "Error %d: %s" % (e.args[0],e.args[1])
        sys.exit(1)
        
    finally:    
            
        if con:    
            con.close()