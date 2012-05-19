'''
Created on May 18, 2012

@author: arthur
'''
from copy import deepcopy

buckets = None
m_size = None
m_boardx = None
m_boardy = None
m_idname = None

class SpacePartitioning():
    '''
    classdocs
    '''
    
    def __init__(self,idname,fixed_size=100,boardx=5000,boardy=5000):
        global buckets
        global m_size
        global m_boardx
        global m_boardy
        global m_idname
        # TODO: board x and y must be multiples of fixed_size
        m_size = fixed_size
        m_boardx = boardx
        m_boardy = boardy
        m_idname = idname
        #buckets = [[None]*boardx]*boardy
        buckets = [[ [] for _ in range(0,m_boardx)] for _ in range(0,m_boardy)]
    
    # Return range
    def __rr__(self,x,y,search_range=10):
        if x - search_range < 0:
            newx = 0
        elif x +search_range > m_boardx:
            newx = m_boardx - 1
        
        if y - search_range < 0:
            newy = 0
        elif y +search_range > m_boardy:
            newy = m_boardy - 1
        
        return range(newx), range(newy)
        
        
    def insert(self,x,y,obj):
        newx,newy = int(x/m_size),int(y/m_size)
        buckets[newx][newy].append(obj)
        
    def delete(self,x,y,objid):
        newx,newy = int(x/m_size),int(y/m_size)
        list_items = buckets[newx][newy]
        for item in list_items:
            if item[m_idname] == objid:
                list_items.remove(item)
        
        
    def retrieve_near(self,x,y,search_range=10):
        newx,newy = int(x/m_size),int(y/m_size)
        rangex,rangey = self.__rr__(newx,newy,search_range)
        result = [] 
        for i in rangex:
            for j in rangey:
                result.append(buckets[i][j])
        return deepcopy(result)
        
                