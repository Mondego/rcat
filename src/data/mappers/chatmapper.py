from data.dataconn import Mapper
import MySQLdb as mdb
import logging
from threading import Timer

from collections import defaultdict

logger = logging.getLogger()

class ChatManager(Mapper):
    db = None
    obm = None
    table = None
    ridname = None
    myid = None
    def __init__(self, datacon):
        global mylocation
        """
        Start the thread that dumps to database
        """
        self.db = datacon.db
        self.obm = datacon.obm
        self.myid = datacon.myid
        #Timer(5.0, self.__dump_to_database__).start()
    
    def retrieve_table_meta(self,table,ridname):
        self.table =  table
        self.ridname = ridname
        self.db.retrieve_table_meta()
    
    def insert(self,id,values):
        owner = self.obm.owner(id)
        if owner != 
        self.db.insert(self.table,values,id)

    
    def update(self,id,update_tuples):
        pass
    
    def select(self,id):
        pass

    @property
    def name(self):
        return "ChatManager"
