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
    def __init__(self,name,mylocation):
        self.name = name
        self.mylocation = mylocation
        self.mapper = None
        self.db = None
        self.obm = None
        