'''
Created on May 18, 2012

@author: arthur
'''
from collections import defaultdict
import logging
from collections import deque

piece_mapper = []
client_mapper = []
idToName = {}
clientScores = defaultdict(int)

m_size = None
m_boardx = None
m_boardy = None
client_loc = {}
object_loc = {}
cur_boardx = None
cur_boardy = None
quadtree = None

class Node():
    tl,tr,bl,br,spl,adm = None, None, None, None, None, None
    
    def __init__(self,spl,adm):
        self.spl = spl
        self.adm = adm
        
    def InsertInNode(self,adm):
        # Leaf node
        if self.adm != None:
            tlsplit = (self.spl[0]/2,self.spl[1]/2)
            trsplit = (self.spl[0]/2 + self.spl[0],self.spl[1]/2)
            self.tl = Node(tlsplit,self.adm)
            self.tr = Node(trsplit,adm)
            self.adm = None
        else:
            # 
            if not self.tl:
                tlsplit = (self.spl[0]/2,self.spl[1]/2)
                self.tl = Node(tlsplit,adm)
            elif not self.tr:
                trsplit = (self.spl[0]/2 + self.spl[0],self.spl[1]/2)
                self.tr = Node(trsplit,adm)
            elif not self.bl:
                blsplit = (self.spl[0]/2,self.spl[1]/2 + self.spl[1])
                self.bl = Node(blsplit,adm)
            elif not self.br:
                brsplit = (self.spl[0]/2 + self.spl[0],self.spl[1]/2 + self.spl[1])
                self.br = Node(brsplit,adm)
            else:
                raise
            
    def FindAndInsert(self,adm):
        q = deque()
        q.append(self)
        while q:
            curnode = q.popleft()
            if (curnode.tl and curnode.tr and curnode.bl and curnode.br):
                q.append(curnode.tl)
                q.append(curnode.tr)
                q.append(curnode.bl)
                q.append(curnode.br)
            else:
                curnode.InsertInNode(adm)
                return

    def find_owner(self,point):
        try:
            if self.adm:
                return self.adm
            
            if (point[0] <= self.spl[0] and point[1] <= self.spl[1]):
                if self.tl:
                    return self.tl.find_owner(point)
            elif (point[0] >= self.spl[0] and point[1] <= self.spl[1]):
                if self.tr:
                    return self.tr.find_owner(point)
                else:
                    return self.tl.adm
            elif (point[0] <= self.spl[0] and point[1] >= self.spl[1]):
                if self.bl:
                    return self.bl.find_owner(point)
                else:
                    if self.tr:
                        return self.tr.adm
                    else:
                        return self.tl.adm
            elif (point[0] >= self.spl[0] and point[1] >= self.spl[1]):
                if self.br:
                    return self.br.find_owner(point)
                else:
                    if self.bl:
                        return self.bl.adm
                    elif self.tr:
                        return self.tr.adm
                    else:
                        return self.tl.adm
        except Exception,e:
            logging.exception("[spacepart]: Quadtree exception:")

class SpacePartitioning():
    db = None
    mylocation = None
    location = None
    datacon = None
    quadtree = None
    table = None
    
    def __init__(self,datacon):
        self.db = datacon.db
        self.myid = datacon.myid
        self.tables = {}
        self.location = {}
        self.datacon = datacon
        
    def create_table(self,table,ridname,clear=False):
        if clear:
            self.datacon.obm.clear(table)
        cmd = "create table if not exists " + table + "(pid varchar(255) not null, b boolean, x int,y int, c int, r int, l varchar(255),primary key(pid))"
        self.datacon.db.create_table(table,cmd,ridname)
        self.ridname = ridname
        self.table = table
        self.datacon.obm.register_node(self.datacon.myid,table,ridname)
        
        # Creates score table
        cmd = "create table if not exists " + table + "_score(user varchar(255) not null, score int,primary key(user))"
        self.datacon.db.create_table(table+"_score",cmd,"user")
        
    def insert(self,values,pid):
        if type(values) is dict:
            values = self.datacon.db.insert_dict_to_list(self.table,values)
        owner = self.quadtree.find_owner((values[2],values[3]))
        if owner == self.myid:
            res = self.datacon.obm.insert(self.table,values,pid)
            if res != True:
                logging.error("[spacepart]: Could not insert. Response: " + str(res))
        else:
            res = self.datacon.obm.insert_remote(self.table,owner,values,pid)
            if res != True:
                logging.error("[spacepart]: Could not insert. Response: " + str(res))
    
    def update(self,x,y,tuples,pid):
        owner = self.quadtree.find_owner((x,y))
        #self.position_object(x, y, pid)
        if owner == self.myid:
            self.datacon.obm.update(self.table,tuples,pid)
            return "LOCAL"
        else:
            self.datacon.obm.update_remote(self.table,owner,tuples,pid)
            return owner
    
    def select_all(self):
        pieces = {}
        objs = self.datacon.obm.find_all(self.table)
        # Returns pairs of rid,host
        for item in objs:
            piece = self.datacon.obm.select(self.table,item["rid"])
            pieces[item["rid"]] = piece
        return pieces
    
    def select(self,x,y,pid):
        owner = self.quadtree.find_owner((x,y))
        if owner == self.myid:
            resp = self.datacon.obm.select(self.table,pid)
        else:
            resp = self.datacon.obm.select_remote(self.table,owner,pid)
        return resp
            
        
    def join(self,settings):
        global m_boardx
        global m_boardy
        global piece_mapper
        global client_mapper
        global quadtree
        
        logging.debug("[spacepart]: Joining a game.")
        
        bw,bh = settings["board"]["w"],settings["board"]["h"]
        m_boardw,m_boardh = int(bw),int(bh)
        bucket_size = int(settings["main"]["bucket_size"])
        """
        TODO: Implement frustrum partitioning
        # Build the bucket matrix for pieces and clients
        line = [ set() for _ in range(0,m_boardw/bucket_size)]
        for _ in range(0,m_boardh/bucket_size):
            piece_mapper.append(deepcopy(line))
        for _ in range(0,m_boardh/bucket_size):
            client_mapper.append(deepcopy(line))
        """ 
        # Build data structure to lookup server responsible for each area. Using Quadtree for now
        adms = set(settings["ADMS"])
        first = adms.pop()
        quadtree = Node((m_boardw/2,m_boardh/2),first)
        for adm in adms:
            print "Inserting in quadtree..."
            quadtree.FindAndInsert(adm)

        self.quadtree = quadtree
        
    def recover_last_game(self):
        allobjs = self.datacon.db.execute("select * from jigsaw")
        self.datacon.db.execute("delete from jigsaw")
        for obj in allobjs:
            self.insert(obj,obj["pid"])
        self.retrieve_score_from_db()
        
        
    """
    ####################################
    SCORE KEEPING SECTION
    ####################################
    """ 
    def retrieve_score_from_db(self):
        global clientScores
        clientScores = {}
        cmd = "select * from " + self.table + "_score"
        result = self.datacon.db.execute(cmd)
        for item in result:
            clientScores[item["user"]] = item["score"]
    
    def schedule_score_update_db(self,username,score):
        # schedules the score update to the database. 
        update_dict = {'score':score}
        self.datacon.db.schedule_update(self.table + "_score", username,update_dict)

    def insert_new_user_score(self,score_tuple):
        self.datacon.db.insert(self.table + "_score",score_tuple)
    
    # Adds new user to the score list, returns the current client scores
    def new_user_connected(self,userid,username):
        idToName[userid] = username
        if not username in clientScores:
            clientScores[username] = 0
            self.insert_new_user_score((username,0))
        return clientScores
    
    # Adds one point to the user name associated with userid, returns a dictionary of modified user name: score pair.
    def add_to_user_score(self,userid):
        username = idToName[userid]
        clientScores[username] += 1
        self.schedule_score_update_db(username,clientScores[username])
        return {username:clientScores[username]}
        
        
    def get_user_scores(self):
        return clientScores
    
    """
    ####################################
    SPACE PARTITIONING MEMORY SECTION
    ####################################
    """ 
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
if __name__ == "__main__":
    adms = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
    rootnode = Node((500,500),0)
    for adm in adms:
        rootnode.FindAndInsert(adm)
    
    print str(rootnode)
    
                