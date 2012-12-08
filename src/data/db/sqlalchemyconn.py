from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import String, Integer
import logging
import sqlalchemy

logger = logging.getLogger()
Base = declarative_base()

# Object Manager tables 
class ObjectManager(Base):
    __tablename__ = '__om__'
    oid = Column(String(255))
    hid = Column(Integer, ForeignKey("hosts.hid"))
    host = relationship("Host",backref="objects",cascade="all, delete, delete-orphan")
    
    def __init__(self,oid):
        self.oid = oid 
            
class Host(Base):
    __tablename__ = '__hosts__'
    hid = Column(String(255), primary_key=True)
    address = Column(String(255))
    
    def __init__(self,hid,address):
        self.hid = hid
        self.address = address

class SQLAlchemyConnector():
    db = None
    engine = None
    def __init__(self, dataconnector, persist_timer=3):
        global datacon
        self.persist_timer = persist_timer
        datacon = dataconnector
        logger.debug("[sqlalchemyconn]: Starting MySQL Connector.")
        
    def open_connections(self, host, user, password, db, poolsize=20, dbtype="mysql"):
        engine = sqlalchemy.create_engine('%s://%s:%s@%s' % (dbtype,user,password,host),pool_size=poolsize) # connect to server
        if dbtype =="mysql":
            engine.execute("CREATE DATABASE IF NOT EXISTS %s" % (db)) #create db
        else:
            engine.execute("CREATE DATABASE %s" % (db)) #create db
        engine.execute("USE %s" % (db)) # select new db
        
        # Set the Session class
        Session = sessionmaker(bind=engine)
        self.engine = engine
        self.Session = Session
        Base.metadata.create_all(self.engine)
        
    def get(self,otype,rid):
        session = self.Session()
        ret = session.query(otype).get(rid)
        session.close()
        return ret
    
    def get_multiple(self,pairs):
        session = self.Session()
        ret_list = []
        # TODO: Can this be improved by chaining a filter? Seems like it
        for otype,rid in pairs:
            ret_list.append(session.query(otype).get(rid))
        session.close()
        return ret_list
    
    def insert_update_multiple(self,objs):
        try:
            session = self.Session()
            for obj in objs:
                session.add(obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
    
    def update(self,otype,rid,tuples):
        try:
            session = self.Session()
            obj = session.query(otype).get(rid)
            for k,v in tuples:
                obj[k] = v
            session.add
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
        
    def insert_update(self,obj):
        try:
            session = self.Session()
            session.add(obj)
            session.commit()
            session.close()
            return True
        except:
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
            return False
    
    def delete(self,otype,rid):
        try:
            session = self.Session()
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
        
    def delete_object(self,obj):
        try:
            session = self.Session()
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
            logger.exception("[sqlalchemyconn]: Error inserting/updating:")
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
            logger.exception("[sqlalchemyconn]: Error filtering:")
            return -1
        
