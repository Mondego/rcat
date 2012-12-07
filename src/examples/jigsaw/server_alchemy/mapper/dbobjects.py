from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from data.db.sqlalchemyconn import Base

class Piece(Base):
    __tablename__ = 'pieces'
    pid = Column(String(255), primary_key=True)
    x = Column(Integer)
    y = Column(Integer)
    c = Column(Integer)
    r = Column(Integer)
    b = Column(Boolean)
    
    uid = Column(Integer, ForeignKey("users.uid"))
    l = relationship("User", backref=backref("pieces"),cascade="all, delete, delete-orphan")

    def __init__(self, pid, x, y, c, r, b):
        self.pid = pid
        self.x = x
        self.y = y
        self.c = c
        self.r = r
        self.b = False

    def __repr__(self):
        return "<Piece(pid:'%s', x:'%s', y:'%s', b:'%s')>" % (self.pid, self.x, self.y, self.b)
    
class User(Base):
    __tablename__ = 'users'
    uid = Column(String(255))
    name = Column(String(255), primary_key=True)
    
    def __init__(self,uid,name):
        self.uid = uid
        self.name = name
            