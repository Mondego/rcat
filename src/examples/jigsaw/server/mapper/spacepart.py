'''
Created on May 18, 2012

@author: arthur
'''
from collections import defaultdict, deque
import logging
from threading import Timer
import time
from copy import deepcopy

piece_mapper = []
client_mapper = []
idToName = {}
clientScores = defaultdict(int)

client_loc = {}
object_loc = {}
cur_boardx = None
cur_boardy = None
quadtree = None

class User():
    uid = None
    frustrum = None
    def __init__(self,uid,frustrum=None):
        self.uid = uid
        self.frustrum = frustrum
    

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
    board= {}
    users = {}
    
    def __init__(self,datacon):
        self.db = datacon.db
        self.myid = datacon.myid
        self.tables = {}
        self.location = {}
        self.datacon = datacon
    
    
    """
    ####################################
    USER MANAGEMENT SECTION
    ####################################
    """ 
        
    def create_user(self,uid):
        if not uid in self.users:
            self.users[uid] = User(uid)
            
    def user_list(self):
        return self.users
    
    def remove_user(self,uid):
        if uid in self.users:
            del self.users[uid]  
    
    def set_user_frustrum(self,uid,frus):
        if not uid in self.users:
            self.users[uid] = User(uid,frus)
        else:
            user = self.users[uid]
            user.frustrum = frus
        self.position_client(frus["x"], frus["y"], user, frus["w"], frus["h"])
        # collect pieces returns a list of sets. Each set represents a bucket
        ids = self.collect_pieces(frus["x"], frus["y"], frus["w"],frus["h"])
        pieces = []
        for set_pieces in ids:
            for pieceid in set_pieces:
                pieces.append(self.datacon.obm.select("jigsaw",pieceid))
        return pieces
                
    def get_user_frustrum(self,uid):
        return self.users[uid].frustrum
    
    
    
    """
    ####################################
    DATA MANAGEMENT SECTION
    ####################################
    """ 
    
    def create_table(self,table,ridname,clear=False):
        if clear:
            self.datacon.obm.clear(table)
        cmd = "create table if not exists " + table + "(pid varchar(255) not null, b boolean, x int,y int, c int, r int, l varchar(255),primary key(pid))"
        self.datacon.db.create_table(table,cmd,ridname)
        self.ridname = ridname
        self.table = table
        self.datacon.obm.register_node(self.datacon.myid,table,ridname)
        self.table_obm = self.table + "_obm"
        self.table_reg = self.table + "_reg"        
        
        # Creates score table
        cmd = "create table if not exists " + table + "_score(pid varchar(255), user varchar(255) not null, score int,primary key(pid))"
        self.table_score = self.table + "_score" 
        self.datacon.db.create_table(table+"_score",cmd,"user")
        
    def dump_last_game(self,keep_score=False):
        self.datacon.db.execute("delete from " + self.table)
        self.datacon.db.execute("delete from " + self.table_obm)
        if not keep_score:
            self.datacon.db.execute("delete from " + self.table_score)
        else:
            # Clear users connected at the time
            self.datacon.db.execute("update set " + self.table_score + " `pid` = ''")
        
    def insert(self,values,pid):
        if type(values) is dict:
            values = self.datacon.db.insert_dict_to_list(self.table,values)
        owner = self.quadtree.find_owner((values[2],values[3]))
        if owner == self.myid:
            res = self.datacon.obm.insert(self.table,values,pid)
            if not res:
                logging.error("[spacepart]: Could not insert. Response: " + str(res))
        else:
            res = self.datacon.obm.insert_remote(self.table,owner,values,pid)
            if not res:
                logging.error("[spacepart]: Could not insert. Response: " + str(res))
    
    def update(self,x,y,tuples,pid):
        owner = self.quadtree.find_owner((x,y))
        if owner == self.myid:
            curpiece = self.datacon.obm.select(self.table,pid)
            self.delete_object(curpiece["x"],curpiece["y"],pid)
            newpiece = self.datacon.obm.update(self.table,tuples,pid)
            self.position_object(x, y, newpiece)
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
            piece = self.datacon.obm.select(self.table,pid)
        else:
            piece = self.datacon.obm.select_remote(self.table,owner,pid)
        return piece
    
            
    """
    ####################################
    MAIN
    ####################################
    """ 
    
    def join(self,settings):
        global piece_mapper
        global client_mapper
        global quadtree
        
        logging.debug("[spacepart]: Joining a game.")
        
        bw,bh = settings["board"]["w"],settings["board"]["h"]
        m_boardw,m_boardh = int(bw),int(bh)
        bucket_size = int(settings["main"]["bucket_size"])
        
        # Build the bucket matrix for pieces and clients
        line = [ set() for _ in range(0,m_boardh/bucket_size)]
        for _ in range(0,m_boardw/bucket_size):
            piece_mapper.append(deepcopy(line))
        line = [ set() for _ in range(0,m_boardh/bucket_size)]
        for _ in range(0,m_boardw/bucket_size):
            client_mapper.append(deepcopy(line))
            
        # Build data structure to lookup server responsible for each area. Using Quadtree for now
        adms = set(settings["ADMS"])
        first = adms.pop()
        quadtree = Node((m_boardw/2,m_boardh/2),first)
        for adm in adms:
            quadtree.FindAndInsert(adm)

        self.quadtree = quadtree
        self.board["bs"] = bucket_size 
        self.board["w"] = m_boardw
        self.board["h"] = m_boardh

    def recover_last_game(self):
        allobjs = self.datacon.db.execute("select * from " + self.table)
        self.dump_last_game(keep_score=True)
        #self.datacon.db.execute("UPDATE SET " + self.table + " `l` = 'None'")
        for obj in allobjs:
            obj['l'] = None
            self.insert(obj,obj["pid"])
        
        
    """
    ####################################
    SCORE KEEPING SECTION
    ####################################
    """ 
    def get_user_scores(self):
        global clientScores
        scores = {}
        scores["top20"] = self.datacon.db.execute("select * from " + self.table_score + " order by score limit 20")
        scores["connected"] = self.datacon.db.execute("select * from " + self.table_score + " where pid<>''")
        return scores
                
    def insert_new_user_score(self,score_tuple):
        self.datacon.db.insert(self.table_score,score_tuple)
    
    # Adds new user to the score list, returns the current client scores
    def new_user_connected(self,userid,username):
        res = self.datacon.db.execute_one("select score from " + self.table_score + " where `user`='" + username + "'")
        if res:
            self.datacon.db.execute("update " + self.table_score + " set `pid`='" + userid + "' where `user`='" + username + "'")
            user_score = res['score']
        else:
            self.datacon.db.insert(self.table_score,[userid,username,0])
            user_score = self.datacon.db.execute_one("select score from " + self.table_score + " where `user`='" + username + "'")['score']
        return {username:user_score}
    
    # Adds one point to the user name associated with userid, returns a dictionary of modified user name: score pair.
    def add_to_user_score(self,userid):
        self.datacon.db.execute("update " + self.table_score + " set score = score + 1 where `pid`='"+ userid + "'")
        res = self.datacon.db.execute_one("select * from " + self.table_score + " where `pid`='" + userid + "'")
        return {res['user']:res['score']}
    
    def disconnect_user(self,userid):
        self.datacon.db.execute("update " + self.table_score + " set `pid`='' where `pid`="+ "'" + userid +"'")
        
    
    """
    ####################################
    SPACE PARTITIONING MEMORY SECTION
    ####################################
    """ 
    def __get_buckets(self,x,y):
        return int(x/self.board["bs"]),int(y/self.board["bs"])
    
    # Return range 
    def __rr__(self,x,y,width,height):
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        x1,y1 = width,height
        if x + width > self.board["w"]:
            x1 = self.board["w"]
        if y + height > self.board["h"]:
            y1 = self.board["h"]
        buktx,bukty = self.__get_buckets(x, y)
        buktx1,bukty1 = self.__get_buckets(x1, y1)
        return range(buktx,buktx1), range(bukty,bukty1)
        
    def position_object(self,x,y,obj):
        try:
            buktx,bukty = self.__get_buckets(x, y)
            piece_mapper[buktx][bukty].add(obj["pid"])
            object_loc[obj["pid"]] = (buktx,bukty)
        except Exception:
            logging.exception("[spacepart]: Error positioning object")

    def position_client(self,x,y,cl,viewx,viewy):
        if cl in client_loc:
            # cl: Tuple with top,left,width and height of client view
            rangex,rangey = self.__rr__(*client_loc[cl])
            for i in rangex:
                for j in rangey:
                    if cl in client_mapper[i][j]:
                        client_mapper[i][j].remove(cl)
                    
        client_loc[cl] = (x,y,viewx,viewy)
        rangex,rangey = self.__rr__(x,y,viewx,viewy)
        for i in rangex:
            for j in rangey:
                client_mapper[i][j].add(cl)
        
        
    def delete_object(self,x,y,objid):
        buktx,bukty = self.__get_buckets(x,y)
        list_items = piece_mapper[buktx][bukty]
        for item in deepcopy(list_items):
            if item == objid:
                list_items.remove(item)
    
    def collect_pieces(self,x,y,x1,y1):
        rangex,rangey = self.__rr__(x,y,x1,y1)
        result = []
        for i in rangex:
            for j in rangey:
                if piece_mapper[i][j]:
                    result.append(piece_mapper[i][j])
        return result
    
if __name__ == "__main__":
    adms = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
    rootnode = Node((500,500),0)
    for adm in adms:
        rootnode.FindAndInsert(adm)
    
    print str(rootnode)
    
                