'''
Created on May 18, 2012

@author: arthur
'''
from copy import deepcopy
import logging

piece_mapper = []
client_mapper = []
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
    def __init__(self,db,idname,board_size=(5000,5000),bucket_size=10):
        global m_idname
        global m_boardx
        global m_boardy
        global piece_mapper
        global client_mapper

        self.db = db
        self.mylocation = db.mylocation
        m_idname = idname
        
        m_boardx,m_boardy = board_size
        
        # Build the bucket matrix for pieces and clients
        line = [ set() for _ in range(0,m_boardx/bucket_size)]
        for _ in range(0,m_boardy/bucket_size):
            piece_mapper.append(deepcopy(line))
        for _ in range(0,m_boardy/bucket_size):
            client_mapper.append(deepcopy(line))
        
    def join(self,partition_x=(0,5000),partition_y=(0,5000)):
        pass
    
    def create(self,puzzle_size=(800,600),partition=(50,50)):
        pass
        
    
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
            piece_mapper[buktx][bukty].add(obj)
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
                    piece_mapper[i][j].remove(cl)
                    
        client_loc[cl] = (buktx,bukty,viewx,viewy)
        rangex,rangey = self.__rr__(buktx,bukty,viewx,viewy)
        for i in rangex:
            for j in rangey:
                piece_mapper[i][j].add(cl)
        
        #client_mapper[buktx][bukty].add(cl)
         
 
    def delete_object(self,x,y,objid):
        buktx,bukty = int(x/m_size),int(y/m_size)
        list_items = piece_mapper[buktx][bukty]
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
                if piece_mapper[i][j]:
                    result.add(piece_mapper[i][j])
        return deepcopy(result)
    """
        
                