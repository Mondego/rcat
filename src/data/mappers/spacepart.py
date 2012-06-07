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
client_loc = {}
object_loc = {}
cur_boardx = None
cur_boardy = None

class SpacePartitioning():
    '''
    classdocs
    '''
    db = None
    mylocation = None
    idname = None
    tables = None
    location = None
    
    def __init__(self,datacon,idname):
        datacon.mapper = self
        self.db = datacon.db
        self.mylocation = datacon.mylocation
        self.idname = idname
        self.tables = {}
        self.location = {}
        
    def join(self,settings):
        global m_boardx
        global m_boardy
        global piece_mapper
        global client_mapper
        
        logging.debug("[spacepart]: Joining a game.")
        
        bx,by = settings["board_size"].split(',')
        m_boardx,m_boardy = int(bx),int(by)
        bucket_size = int(settings["bucket_size"])
        
        # Build the bucket matrix for pieces and clients
        line = [ set() for _ in range(0,m_boardx/bucket_size)]
        for _ in range(0,m_boardy/bucket_size):
            piece_mapper.append(deepcopy(line))
        for _ in range(0,m_boardy/bucket_size):
            client_mapper.append(deepcopy(line))
        
    
    def create(self,settings,servers):
        bx,by = settings["board_size"].split(',')
        boardx,boardy = int(bx),int(by)
        
        logging.debug("[spacepart]: Starting a new game.")
        # Partition the board across all existing servers
        part = {}
        for srv in servers:
            part[srv] = ((0,0),(boardx,boardy))
        
        return part
        
    
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
            if item[self.idname] == objid:
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
        
                