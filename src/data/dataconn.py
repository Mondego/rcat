'''
Created on May 25, 2012

@author: arthur
'''

from abc import ABCMeta, abstractmethod, abstractproperty

class Mapper:
    __metaclass__ = ABCMeta
    @abstractproperty
    def name(self):
        pass
    
    @abstractmethod
    def select(self):
        pass

    def update(self):
        pass

    @abstractmethod
    def insert(self):
        pass

class DataConnector():
    myid = None
    name = None
    mapper = None
    db = None
    obm = None
    host = None
    
    def __init__(self,name,id):
        self.name = name
        self.myid = id
