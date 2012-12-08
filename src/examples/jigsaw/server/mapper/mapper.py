'''
Created on May 18, 2012

@author: arthur
'''
from collections import defaultdict, deque
from copy import deepcopy
from examples.jigsaw.server.mapper.dbobjects import User, Piece
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
from threading import Timer
import logging
import time

idToName = {}

client_loc = {}
object_loc = {}
cur_boardx = None
cur_boardy = None
quadtree = None

class Node():
    tl, tr, bl, br, spl, adm = None, None, None, None, None, None

    def __init__(self, spl, adm):
        self.spl = spl
        self.adm = adm

    def InsertInNode(self, adm):
        # Leaf node
        if self.adm != None:
            tlsplit = (self.spl[0] / 2, self.spl[1] / 2)
            trsplit = (self.spl[0] / 2 + self.spl[0], self.spl[1] / 2)
            self.tl = Node(tlsplit, self.adm)
            self.tr = Node(trsplit, adm)
            self.adm = None
        else:
            # 
            if not self.tl:
                tlsplit = (self.spl[0] / 2, self.spl[1] / 2)
                self.tl = Node(tlsplit, adm)
            elif not self.tr:
                trsplit = (self.spl[0] / 2 + self.spl[0], self.spl[1] / 2)
                self.tr = Node(trsplit, adm)
            elif not self.bl:
                blsplit = (self.spl[0] / 2, self.spl[1] / 2 + self.spl[1])
                self.bl = Node(blsplit, adm)
            elif not self.br:
                brsplit = (self.spl[0] / 2 + self.spl[0], self.spl[1] / 2 + self.spl[1])
                self.br = Node(brsplit, adm)
            else:
                raise

    def FindAndInsert(self, adm):
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

    def find_owner(self, point):
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
        except Exception, e:
            logging.exception("[spacepart]: Quadtree exception:")

class JigsawMapper():
    db = None
    mylocation = None
    location = None
    datacon = None
    quadtree = None
    table = None
    board = {}
    users = {}

    def __init__(self, datacon):
        self.myid = datacon.myid
        self.datacon = datacon

    """
    ####################################
    USER MANAGEMENT SECTION
    ####################################
    """
    """
    ####################################
    DATA MANAGEMENT SECTION
    ####################################
    """

    def connected_users(self):
        session = self.datacon.db.Session()
        res = session.query(User).filter(User.uid != None).all()
        session.close()
        return res

    def start(self, otypes, clear=False):
        if clear:
            self.datacon.obm.clear()
        self.datacon.obm.register_node(self.datacon.myid, otypes)

    def dump_pieces(self):
        self.datacon.db.clear([Piece])

    def reset_players(self, keep_score, keep_users):
        try:
            if not keep_score:
                if not keep_users:
                    # Don't keep any information. Used for initialization.
                    self.datacon.db.clear([User])
                else:
                    # Keep the connected users on the table and change their scores to 0.
                    session = self.datacon.db.Session()
                    session.query(User).filter(User.uid==None).delete()
                    session.query(User).update({'score':0})
                    session.commit()
                    session.close()
            else:
                # Keep the connected users and their scores.
                session = self.datacon.db.Session()
                session.query(User).filter(User.uid==None).delete()
                session.commit()
                session.close()
                self.datacon.db.execute("update " + self.table_score + " set `uid` = ''")
            return True
        except:
            logging.exception("[mapper]: Failed to reset players:")
            return False

    def get_piece(self, pid):
        piece = self.datacon.obm.get(Piece,pid)
        return piece

    # Inserts directly, OBM caches on selects
    def create_pieces(self, pieces):
        self.datacon.db.insert_update_multiple(pieces)

    # Inserts through OBM, thus creating the caches of objects created
    def insert_piece(self, piece):
        res = self.datacon.obm.put(Piece, piece, piece['pid'])
        if not res:
            logging.error("[mapper]: Could not insert. Response: " + str(res))

    def move_piece(self, pid, tuples):
        # TODO: Determine what server should start treating this piece movement (load balance function). For now, treat it here.
        # Transfer piece locally, as I expect new move piece requests soon
        if self.datacon.obm.whereis(Piece,pid) != self.myhostid:
            res = self.datacon.obm.relocate(Piece,pid,None,self.myid)
        
        if not res:
            logging.error("[mapper]: Could not find piece.")
            return False
        
        res = self.datacon.obm.post(Piece,pid,tuples,self.myid)
        if not res:
            logging.error("[mapper]: Could not update piece.")
            return False
        return True
        
    def lock_piece(self, pid, uid):
        piece = self.datacon.obm.get(pid)
        user = self.datacon.obm.get(uid)
        if not piece.l and not piece.b:
            ret = self.datacon.obm.post(Piece,piece['pid'],{'l':user},None,True)
            if not ret:
                logging.error("[mapper]: Could not lock piece.")
                return False
        else:
            # If piece is locked already, return false
            return False
        
    def bind_piece(self, pid, tuples):
        ret = self.datacon.obm.post(Piece,pid,tuples,None,True)
        if not ret:
            logging.error("[mapper]: Could not bind piece.")
            return False
        else:
            return True
        
    def select_all(self):
        # TODO: From database?
        return self.datacon.obm.find_all(Piece)


    """
    ####################################
    MAIN
    ####################################
    """

    def join(self, settings):
        global piece_mapper
        global client_mapper
        global quadtree

        logging.debug("[spacepart]: Joining a game.")

        bw, bh = settings["board"]["w"], settings["board"]["h"]
        m_boardw, m_boardh = int(bw), int(bh)
        bucket_size = int(settings["main"]["bucket_size"])

        # Build data structure to lookup server responsible for each area. Using Quadtree for now
        self.adms = set(settings["ADMS"])

        self.board["bs"] = bucket_size
        self.board["w"] = m_boardw
        self.board["h"] = m_boardh

    def recover_last_game(self):
        try:
            session = self.datacon.db.Session()
            session.query(User).update({'uid':None})
            session.query(Piece).update({'l':None})
            session.commit()
            session.close()
        except:
            logging.exception("[mapper]: Could not recover last game:")
        
        
    """
    ####################################
    SCORE KEEPING SECTION
    ####################################
    """
    # TODO: Externalize as a score keeping service. 
    # This score service would buffer score transactions between DB and servers.
    def get_user_scores(self, num_top):
        """ Return the top X player scores """
        scores = {}
        try:
            session = self.datacon.db.Session()
            scores["numTop"] = session.query(User).order_by(desc(User.score)).limit(num_top).all()
            scores["connected"] = session.query(User).filter(User.uid!=None).all()
        except:
            logging.exception("[mapper]: Could not retrieve scores:")
            return False
        return scores

    # Adds new user to the score list, returns the current client scores
    def new_user_connected(self, userid, username):
        if username == "Guest":
            return None
        try:
            session = self.datacon.db.Session()
            user = session.query(User).get(username)
            if user:
                user.uid = userid
                score = user.score
            else:
                user = User(userid, username, 0)
                score = 0
                
            session.add(user)
            session.commit()
            session.close()    
        except:
            logging.exception("[mapper]: Could not add new user to score table.")
        
        return [{'user':username, 'uid':userid, 'score':score}]

    # Adds one point to the user name associated with userid, returns a dictionary of modified user name: score pair.
    def add_to_user_score(self, userid):
        try:
            session = self.datacon.db.Session()
            user = session.query(User).filter(User.uid==userid).one()
            if user:
                user.score += 1
                session.add(user)
                session.commit()
            else:
                logging.error("[mapper]: User could not be found in database.")
                return False
            session.close()
            return [{'user':user.name, 'uid':userid, 'score':user.score}]
        
        except:
            logging.exception("[mapper]: Could not add user score.")
            return False

    def disconnect_user(self, userid):
        try:
            session = self.datacon.db.Session()
            user = session.query(User).filter(User.uid==userid).one()
            user.uid = None
            
            locked_pieces = session.query(Piece).filter(Piece.l==userid).all()
            
            if not locked_pieces:
                # Lets wait a bit if another node is taking its time to persist the locked object
                time.sleep(self.datacon.db.persist_timer*2)
                locked_pieces = session.query(Piece).filter(Piece.l==userid).all()
                
            if locked_pieces:
                # There should be only one piece here!
                for piece in locked_pieces:
                    piece['l'] = None
                    session.add(piece)
                    
            session.commit()
            session.close()
            
        except NoResultFound:
            logging.debug("[mapper]: User was not found in database. Should be ok.")
            return True
        except:
            logging.exception("[mapper]: Error while trying to remove user from connected list:")
            return False
        return True
