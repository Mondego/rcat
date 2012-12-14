from copy import deepcopy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, subqueryload
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import String, Integer
from threading import Timer
import logging
import sqlalchemy
import time

logger = logging.getLogger()
Base = declarative_base()

# Object Manager tables 
class ObjectManager(Base):
    __tablename__ = 'objectmanager'
    oid = Column(String(255),primary_key=True)
    hid = Column(String(255), ForeignKey("hosts.hid"))
    host = relationship("Host",backref="objects",cascade="all, delete",single_parent=True)
    
    def __init__(self,oid):
        self.oid = oid
                    
class Host(Base):
    __tablename__ = 'hosts'
    hid = Column(String(255), primary_key=True)
    address = Column(String(255))
    
    def __init__(self,hid,address):
        self.hid = hid
        self.address = address

class SQLAlchemyConnector():
    db = None
    engine = None
    updates = None
    
    def __init__(self, dataconnector, persist_timer=3):
        global datacon
        self.persist_timer = persist_timer
        datacon = dataconnector
        update = Timer(5.0, self.__perform_updates__,[self.persist_timer])
        update.daemon = True
        update.start()
        self.updates = {}
        logger.debug("[sqlalchemyconn]: Starting MySQL Connector.")
        
    def __perform_updates__(self,persist_timer):
        while(1):
            try:
                if self.engine:
                    conn = self.engine.connect()
                    trans = conn.begin()
                    for typeob,list_updates in self.updates.items():
                        for oid,updates in list_updates.items():
                            try:
                                conn.execute(typeob.__table__.update().where(list(typeob.__table__.primary_key)[0]==oid).values(updates))
                            except:
                                logger.exception("[sqlalchemyconn]: Error commiting scheduled updates:")
                    trans.commit()
                    # Closing this connection does not mean closing the actual connection to then database.
                    # http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Connection.connect
                    conn.close()
            except:
                logger.exception("[sqlalchemyconn]: Error executing update thread:")
            time.sleep(persist_timer)
        
    
    def schedule_update(self,otype,oid,update_dict):
        if not otype in self.updates:
            self.updates[otype] = {}
        self.updates[otype][oid] = deepcopy(update_dict)
        return True
        
    def open_connections(self, host, user, password, db, poolsize=20, dbtype="mysql"):
        engine = sqlalchemy.create_engine('%s://%s:%s@%s' % (dbtype,user,password,host),pool_size=poolsize,echo=False) # connect to server
        if dbtype =="mysql":
            engine.execute("CREATE DATABASE IF NOT EXISTS %s" % (db)) #create db
        else:
            engine.execute("CREATE DATABASE %s" % (db)) #create db
        engine = sqlalchemy.create_engine('%s://%s:%s@%s/%s' % (dbtype,user,password,host,db),pool_size=poolsize,echo=False) # connect to server
        
        # Set the Session class
        Session = sessionmaker(bind=engine)
        self.engine = engine
        self.Session = Session
        Base.metadata.create_all(self.engine)
        
    def get(self,otype,rid,eager_list=False):
        session = self.Session()
        qry = session.query(otype)
        if eager_list:
            for rel in eager_list:
                qry = qry.options(subqueryload(rel))
        ret = qry.get(rid)
        session.close()
        return ret
    
    def get_multiple(self,pairs):
        try:
            session = self.Session()
            ret_list = []
            # TODO: Can this be improved by chaining a filter? Seems like it
            for otype,rid in pairs:
                ret_list.append(session.query(otype).get(rid))
            session.close()
            return ret_list
        except:
            logger.exception("[sqlalchemyconn]: Error getting multiple:")
            return False
    
    def insert_update_multiple(self,objs,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            for obj in objs:
                session.add(obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting multiple:")
            return False
    
    def update(self,otype,oid,update_dict,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            conn = self.engine.connect()
            conn.execute(otype.__table__.update().where(list(otype.__table__.primary_key)[0]==oid).values(update_dict))
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error updating:")
            return False
        
    def merge(self,source_obj,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            session.merge(source_obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error updating:")
            return False
        
    def insert(self,obj,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            session.add(obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
        
    def insert_update(self,obj,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            session.add(obj)
            session.commit()
            session.close()
            logger.info("x: %s, y: %s" % (obj.x,obj.y))
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
    
    def delete(self,otype,rid,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            obj = session.query(otype).get(rid)
            if obj:
                session.delete(obj)
                session.commit()
            else:
                logger.error("[sqlalchemyconn]: Could not find object to delete.")
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
        
    def delete_object(self,obj,expire=False):
        try:
            session = self.Session(expire_on_commit=expire)
            session.delete(obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
        
    # Takes a list of object types to clear the table
    def clear(self,objtypes):
        try:
            session = self.Session()
            for otype in objtypes:
                session.query(otype).delete()
                session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error clearing:")
            return False

    def return_all(self,otype):
        try:
            session = self.Session()
            res = session.query(otype).all()
            session.close()
            return res
        except:
            logger.exception("[sqlalchemyconn]: Error returning all:")
            return []
    
    # Returns all value of object type otype where param == value.
    def filter(self,otype,param,value):
        try:
            session = self.Session()
            res = session.query(otype).filter(param==value).all()
            session.close()
            return res
        except:
            logger.exception("[sqlalchemyconn]: Error filtering:")
            return []
        
    def count(self,otype):
        try:
            session = self.Session()
            res = session.query(otype).count()
            session.close()
            return res
        except:
            logger.exception("[sqlalchemyconn]: Error counting:")
            return -1
        
    """
    Object Manager Methods (private)
    """
    def _obm_replace_host(self,oid,hid):
        try:
            session = self.Session()
            obj = session.query(ObjectManager).get(oid)
            newhost = session.query(Host).get(hid)
            obj.host = newhost
            session.add(obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error transferring host.")
            return False
