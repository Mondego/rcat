from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from data.db.sqlalchemyconn import Base
import json
import logging

class Piece(Base):
    __tablename__ = 'pieces'
    pid = Column(String(255), primary_key=True)
    x = Column(Integer)
    y = Column(Integer)
    c = Column(Integer)
    r = Column(Integer)
    b = Column(Boolean)
    l = Column(String(255))

    def __init__(self, pid, x, y, c, r, b, l):
        self.pid = pid
        self.x = x
        self.y = y
        self.c = c
        self.r = r
        self.b = False
        self.l = l

    def __repr__(self):
        return "<Piece(pid:'%s', x:'%s', y:'%s', b:'%s', l:'%s')>" % (self.pid, self.x, self.y, self.b, self.l)
    
class User(Base):
    __tablename__ = 'users'
    uid = Column(String(255))
    name = Column(String(255), primary_key=True)
    score = Column(Integer,default=0,nullable=False)
    
    def __init__(self,uid,name,score):
        self.uid = uid
        self.name = name
        self.score = score

def dumps_piece(ap):
    piece = {}
    piece['pid'] = ap.pid
    piece['x'] = ap.x
    piece['y'] = ap.y
    piece['c'] = ap.c
    piece['r'] = ap.r
    piece['b'] = ap.b
    piece['l'] = ap.l
    return piece
    
def loads_piece(dp,session,commit=False):
    try:
        session.start()
        piece = Piece(dp['pid'],None,None,None,None,None)

        if 'x' in dp:
            piece.x = dp['x']
        if 'y' in dp:
            piece.y = dp['y']
        if 'c' in dp:
            piece.c = dp['c']
        if 'r' in dp:
            piece.r = dp['r']
        if 'b' in dp:
            piece.b = dp['b']
        if 'l' in dp:
            piece.l = dp['l']
        if commit:
            session.add(piece)
            session.commit()
        session.close()
        return piece
    except:
        logging.exception("[dbobjects]: Error loading a piece.")
    
def dumps_userscore(list_users):
    scores = []
    for user in list_users:
        scores.append({'uid':user.uid,'score':user.score,'user':user.name})
    return scores
    