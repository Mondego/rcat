'''
Created on May 18, 2012

@author: arthur
'''
from copy import deepcopy
import logging
import math

piece_mapper = []
client_mapper = []
m_size = None
m_boardx = None
m_boardy = None
client_loc = {}
object_loc = {}
cur_boardx = None
cur_boardy = None
quadtree = None

def BuildQuadTree(node,adms):
    if adms:
        adms.append(node.adm)
        node.adm = None
    else:
        return
    
    tladm = adms.pop()
    tlsplit = (node.spl[0]/2,node.spl[1]/2)
    node.tl = Node(tlsplit,tladm)
        
    if adms:
        tradm = adms.pop()
        trsplit = (node.spl[0]/2 + node.spl[0],node.spl[1]/2)
        node.tr = Node(trsplit,tradm)
    
    if adms:
        bladm = adms.pop()
        blsplit = (node.spl[0]/2,node.spl[1]/2 + node.spl[1])
        node.bl = Node(blsplit,bladm)
    
    if adms:
        bradm = adms.pop()
        brsplit = (node.spl[0]/2 + node.spl[0],node.spl[1]/2 + node.spl[1])
        node.br = Node(brsplit,bradm)
        
    if not adms:
        return 
    
    BuildQuadTree(node.tr,adms)
    BuildQuadTree(node.tl,adms)
    BuildQuadTree(node.bl,adms)
    BuildQuadTree(node.br,adms)
   
class Node():
    tl,tr,bl,br,spl,adm = None, None, None, None, None, None
    
    def __init__(self,spl,adm):
        self.spl = spl
        self.adm = adm
        
    def insert(self):
        raise
    
    def find_owner(self,point):
        if self.adm:
            return self.adm
        
        if (point[0] <= self.split[0] and point[1] >= self.split[0]):
            if self.tl:
                return self.tl.find_owner(point)
        elif (point[0] >= self.split[0] and point[1] >= self.split[0]):
            if self.tr:
                return self.tl.find_owner(point)
            else:
                return self.tl.adm
        elif (point[0] <= self.split[0] and point[1] <= self.split[0]):
            if self.bl:
                return self.bl.find_owner(point)
            else:
                if self.tr:
                    return self.tr.adm
                else:
                    return self.tl.adm
        elif (point[0] >= self.split[0] and point[1] <= self.split[0]):
            if self.br:
                return self.br.find_owner(point)
            else:
                if self.bl:
                    return self.bl.adm
                elif self.tr:
                    return self.tr.adm
                else:
                    return self.tl.adm

"""
class Node():
    tl,tr,bl,br,split,adm = None, None, None, None, None, None
    
    def __init__(self,spl,adms,adm):
        self.split = spl
        if adms:
            adms.append(adm)
            self.adm = None
        else:
            self.adm = adm
            return
        
        tladm = adms.pop()
        tlsplit = (spl[0]/2,spl[1]/2)
        if adms:
            tradm = adms.pop()
            trsplit = (spl[0]/2 + spl[0],spl[1]/2)
        
        if adms:
            bladm = adms.pop()
            blsplit = (spl[0]/2,spl[1]/2 + spl[1])
        
        if adms:
            bradm = adms.pop()
            brsplit = (spl[0]/2 + spl[0],spl[1]/2 + spl[1])
        
        self.tl = Node(tlsplit,adms,tladm)
        if tradm:
            self.tr = Node(trsplit,adms,tradm)
        if bladm:
            self.bl = Node(blsplit,adms,bladm)
        if bradm:
            self.br = Node(brsplit,adms,bradm)
"""
        
    
class SpacePartitioning():
    '''
    classdocs
    '''
    db = None
    mylocation = None
    tables = None
    location = None
    
    def __init__(self,datacon):
        self.db = datacon.db
        self.mylocation = datacon.mylocation
        self.tables = {}
        self.location = {}
        
    def join(self,settings):
        global m_boardx
        global m_boardy
        global piece_mapper
        global client_mapper
        global quadtree
        
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
            
        adms = set(settings["ADMS"])
        first = adms.pop()
        quadtree = Node((m_boardx/2,m_boardy/2),adms,first)
        # Build data structure to lookup server responsible for each area. Using Quadtree for now
        
    
        
    def create(self,settings,servers):
        # Needs a better algorithm, but for now, attempts to break the board into a squared division
        bx,by = settings["board_size"].split(',')
        boardx,boardy = int(bx),int(by)
        
        logging.debug("[spacepart]: Starting a new game.")
    
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
         
    """
    def delete_object(self,x,y,objid):
        buktx,bukty = int(x/m_size),int(y/m_size)
        list_items = piece_mapper[buktx][bukty]
        for item in list_items:
            if item[self.idname] == objid:
                list_items.remove(item)
    
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
        
                