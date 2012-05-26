'''
Created on May 18, 2012

@author: arthur
'''
from copy import deepcopy
import logging

buckets = None
client_buckets = None
m_size = None
m_boardx = None
m_boardy = None
m_idname = None
client_loc = {}
object_loc = {}
cur_boardx = None
cur_boardy = None

class SpacePartitioning():
    '''
    classdocs
    '''
    def __init__(self,idname,board_size=(5000,5000),partition_x=(0,5000),partition_y=(0,5000)):
        global buckets
        global client_buckets
        global m_size
        global m_boardx
        global m_boardy
        global m_idname
        m_boardx,m_boardy = board_size
        m_idname = idname
        buckets = [[ set() for _ in range(0,m_boardx)] for _ in range(0,m_boardy)]
        client_buckets = [[ set() for _ in range(0,m_boardx)] for _ in range(0,m_boardy)]
    
    # Return range
    def __rr__(self,x,y,width,height):
        if x + width > m_boardx:
            buktx = m_boardx - 1
        if y + height > m_boardy:
            bukty = m_boardy - 1
        return range(buktx), range(bukty)
        
    def position_object(self,x,y,obj):
        try:
            buktx,bukty = int(x/m_size),int(y/m_size)
            buckets[buktx][bukty].add(obj)
            object_loc[obj] = (buktx,bukty)
        except Exception as e:
            logging.error(e)

    def position_client(self,x,y,cl,viewx,viewy):
        buktx,bukty = int(x/m_size),int(y/m_size)
        if cl in client_loc:
            # cl: Tuple with top,left,width and height of client view
            rangex,rangey = self.__rr__(*client_loc[cl])
            for i in rangex:
                for j in rangey:
                    buckets[i][j].remove(cl)
                    
        client_loc[cl] = (buktx,bukty,viewx,viewy)
        rangex,rangey = self.__rr__(buktx,bukty,viewx,viewy)
        for i in rangex:
            for j in rangey:
                buckets[i][j].add(cl)
        
        #client_buckets[buktx][bukty].add(cl)
         
 
    def delete_object(self,x,y,objid):
        buktx,bukty = int(x/m_size),int(y/m_size)
        list_items = buckets[buktx][bukty]
        for item in list_items:
            if item[m_idname] == objid:
                list_items.remove(item)
    """
    def retrieve_near(self,x,y,search_range=10):
        buktx,bukty = int(x/m_size),int(y/m_size)
        rangex,rangey = self.__rr__(buktx,bukty,search_range)
        result = []
        for i in rangex:
            for j in rangey:
                if buckets[i][j]:
                    result.add(buckets[i][j])
        return deepcopy(result)
    """
        
                