from data.dataconn import Mapper
import MySQLdb as mdb
import logging
from threading import Timer
import warnings

from collections import defaultdict

logger = logging.getLogger()

class ChatManager(Mapper):
    rooms = None
    ridname = None
    table = None
    datacon = None
    def __init__(self, datacon):
        self.datacon = datacon
        
    def newroom(self,newroom):
        self.rooms[newroom] = {}
        
    def create_table(self,table,ridname):
        self.datacon.obm.clear(table)
        cmd = "create table if not exists " + table + "(mid mediumint not null auto_increment,uid varchar(255) not null,message varchar(255), primary key(mid))"
        self.datacon.db.execute(cmd)
        self.datacon.db.retrieve_table_meta(table,ridname)
        self.ridname = ridname
        self.table = table
        
        self.datacon.obm.register_node(self.datacon.myid,table,ridname,"mediumint",0)
        self.datacon.obm.create_index(table,"uid")
    
    def insert(self,values):
        self.datacon.obm.insert(self.table,values)
    
    def update(self,rid,update_tuples):
        return self.datacon.obm.update(self.table,rid)
    
    def select(self,rid):
        return self.datacon.obm.select(self.table,rid)
    
    def select_per_user(self,uid):
        return self.datacon.obm.select_diff_index(self.table,uid,'uid')

    @property
    def name(self):
        return "ChatManager"
