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
    def __init__(self,name,mapper=None,db=None,obm=None):
        self.mapper = mapper
        self.db = db
        self.obm = obm
        self.name = name