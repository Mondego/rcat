'''
Created on May 18, 2012

@author: arthur
'''
from collections import deque
from examples.jigsaw.server.mapper.dbobjects import User, Piece, dumps_piece, \
    loads_piece, dumps_userscore
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
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
    started = False

    def __init__(self, datacon):
        self.myid = datacon.myid
        self.datacon = datacon
        # Set of userids who are Guests (no score)
        self.guests = set()

    """
    ####################################
    RCAT SECTION
    ####################################
    """
    """
    cleanup_obm(): Starts Object Manager by clearing out all previous entries for hosts and objects. Must only be run ONCE, and before every
    other node starts registering.
    """
    def cleanup_obm(self):
        self.datacon.obm.clear()
    
    """
    init_obm(otypes): Tells the OBM which objects will be cacheable, so it can prepare for caching.
    """ 
    def init_obm(self, otypes):
        if not self.started:
            self.datacon.obm.register_node(self.datacon.myid, otypes)
            self.started = True

    """
    ####################################
    GAME INIT SECTION
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
        
        self.clear_piece_cache()

    def recover_last_game(self):
        try:
            session = self.datacon.db.Session(expire_on_commit=False)
            session.query(User).update({'uid':None})
            session.query(Piece).update({'l':None})
            session.commit()
            session.close()
        except:
            logging.exception("[mapper]: Could not recover last game:")
        
                

    """
    ####################################
    GAME DATA MANAGEMENT SECTION
    ####################################
    """

    def disconnect_user(self, userid):
        try:
            if userid in self.guests:
                self.guests.remove(userid)
            session = self.datacon.db.Session()
            user = session.query(User).filter(User.uid==userid).one()
            user.uid = None
            
            locked_pieces = session.query(Piece).filter(Piece.l==userid).all()
            session.commit()
            
            if not locked_pieces:
                # Lets wait a bit if another node is taking its time to persist the locked object
                time.sleep(self.datacon.db.persist_timer*2)
                locked_pieces = session.query(Piece).filter(Piece.l==userid).all()
                
            if locked_pieces:
                # There should be only one piece here!
                for piece in locked_pieces:
                    piece.l = None
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

    # returns a list of uuids of all connected users, named and guests
    """
    FIX: Not taking into account guests yet
    def connected_users(self):
        session = self.datacon.db.Session(expire_on_commit=False)
        res = session.query(User).filter(User.uid != None).all()
        session.close()
        return res
    """
    
    def get_guests(self):
        return self.guests

    def dump_pieces(self):
        self.datacon.db.clear([Piece])
    
    def clear_piece_cache(self):
        return self.datacon.obm.clear_cache([Piece])

    def reset_game(self, keep_score=False, keep_users=False, keep_pieces=False):
        session = self.datacon.db.Session(expire_on_commit=False)
        try:
            if not keep_score:
                if not keep_users:
                    # Don't keep any information. Used for initialization.
                    self.datacon.db.clear([User])
                else:
                    # Keep the connected users on the table and change their scores to 0.
                    session.query(User).filter(User.uid==None).delete()
                    session.query(User).update({'score':0})
                    session.commit()
            else:
                # Keep the connected users and their scores.
                session.query(User).filter(User.uid==None).delete()
                session.commit()
                
                self.datacon.db.execute("update " + self.table_score + " set `uid` = ''")

            if not keep_pieces:
                # Clean from database
                session.query(Piece).delete()
                session.commit()
                # Clean from cache
                self.clear_piece_cache()
        except:
            logging.exception("[mapper]: Failed to reset players:")
            return False
        session.close()
        return True

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

    def move_piece(self, pid, newpos):
        # TODO: Determine what server should start treating this piece movement (load balance function). For now, treat it here.
        # Transfer piece locally, as I expect new move piece requests soon
        res = True
        if self.datacon.obm.whereis(Piece,pid) != self.myid:
            res = self.datacon.obm.relocate(Piece,pid,None,self.myid)
        
        if not res:
            logging.error("[mapper]: Could not find piece.")
            return False
        
        res = self.datacon.obm.post(Piece,pid,newpos,self.myid)
        if not res:
            logging.error("[mapper]: Could not update piece.")
            return False
        return True

    def drop_piece(self, pid, update_dict):
        res = self.datacon.obm.post(Piece,pid,update_dict,None,True)
        if not res:
            logging.error("[mapper]: Could not drop piece.")
            return False
        else:
            return True
        
    def lock_piece(self, pid, uid):
        return self.lock_piece_local(pid,uid)
        
    # Returns if piece locking the piece was successful or not.
    def lock_piece_local(self, pid, uid):
        piece = self.datacon.obm.get_lazy(Piece,pid)
        if not piece:
            piece = self.datacon.db.get(Piece,pid)

        # If it is already bound, I can't lock it, return false
        if piece.b:
            return False

        if piece.l:
            # If piece is locked, and but locked to the right user, everything went better than expected!
            if piece.l == uid:
                return True
            else:
                # Someone else owns the lock, can't lock it!
                return False
        # If piece is not locked, move it to here if necessary, then lock it
        else:
            obj_location = self.datacon.obm.whereis(Piece,pid)
            logging.debug("[mapper]: I think the object is in %s" % obj_location)
            res = True
            if obj_location:
                if obj_location != self.myid:
                    logging.debug("[mapper]: Not here. Relocating from %s" % obj_location)
                    res = self.datacon.obm.relocate(Piece,pid,None,self.myid)
            else:
                logging.debug("[mapper]: Don't know where it is. Attempting to relocate anyway.")
                res = self.datacon.obm.relocate(Piece,pid,None,self.myid)
            
            # Double check if its here.  
            if not res:
                logging.error("[mapper]: Could not transfer piece locally. Attempting database locking.")
                res = self.lock_piece_db(pid, uid)
                
            if not res:
                logging.error("[mapper]: Could not lock piece remotely either. Giving up.")
                return False
                
            # Piece is here and ready to be updated!
            res = self.datacon.obm.post(Piece,piece.pid,{'l':uid},self.myid,True)
            if not res:
                    logging.error("[mapper]: Could not lock piece.")
                    return False
            else:
                return True
        
    def lock_piece_db(self, pid, uid):
        # Requires a session, since locks must be atomic. Database is used instead of OBM for locking.
        try:
            session = self.datacon.db.Session()
            piece = session.query(Piece).get(pid)
            if not piece.l and not piece.b:
                piece.l = uid
                session.add(piece)
                session.commit()
                
                # Need to inform the object owner of the change.
                ret = self.datacon.obm.post(Piece,piece.pid,{'l':uid},None,False,False)
                if not ret:
                    logging.error("[mapper]: Could not lock piece.")
                    return False
                session.close()
                return True
            else:
                # If piece is locked already, return false
                session.close()
                return False
            
        except:
            logging.exception("[mapper]: Could not lock piece:")
            return False
        
    def bind_piece(self, pid, tuples):
        ret = self.datacon.obm.post(Piece,pid,tuples,None,True)
        if not ret:
            logging.error("[mapper]: Could not bind piece.")
            return False
        else:
            return True
    
    def get_user(self, uid):
        try:
            session = self.datacon.db.Session(expire_on_commit=False)
            res = session.query(User).filter(User.uid==uid).one()
            return res
        except:
            logging.exception("[mapper]: Retrieving user returned an error:")
            return False
    
    def select_all(self):
        # TODO: From database?
        all_pieces = self.datacon.obm.find_all(Piece)
        enc_pieces = {}
        for piece in all_pieces:
            enc_pieces[piece.pid] = dumps_piece(piece)
        return enc_pieces
    
    def game_over(self, total_pieces):
        try:
            session = self.datacon.db.Session()
            res = session.query(Piece).filter(Piece.b==1).count()
            session.close()
            if res < total_pieces:
                return False
            else:
                return True
        except:
            logging.exception("[mapper]: Counting pieces went wrong:")
            return False



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
            session = self.datacon.db.Session(expire_on_commit=False)
            scores["numTop"] = num_top
            # These queries return User objects, they need to be serialized for client.
            top_users = session.query(User).order_by(desc(User.score)).limit(num_top).all()
            conn_users = session.query(User).filter(User.uid!=None).all()
            scores["top"] = dumps_userscore(top_users)
            scores["connected"] = dumps_userscore(conn_users)
        except:
            logging.exception("[mapper]: Could not retrieve scores:")
            return False
        return scores

    # Adds new user to the score list, returns the current client scores
    def new_user_connected(self, userid, username):
        if username == "Guest":
            self.guests.add(userid)
            return None
        try:
            session = self.datacon.db.Session(expire_on_commit=False)
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
            return [{'user':username, 'uid':userid, 'score':score}]    
        except:
            logging.exception("[mapper]: Could not add new user to score table.")
        return False
        

    # Adds one point to the user name associated with userid, returns a dictionary of modified user name: score pair.
    def add_to_user_score(self, userid):
        try:
            # If user is not a guest
            if userid not in self.guests:
                session = self.datacon.db.Session(expire_on_commit=False)
                user = session.query(User).filter(User.uid==userid).one()
                if user:
                    user.score += 1
                    session.add(user)
                    session.commit()
                else:
                    logging.debug("[mapper]: User could not be found in database. Probably a Guest. User id was %s" % (userid))
                    return False
                session.close()
                return [{'user':user.name, 'uid':userid, 'score':user.score}]
        
        except:
            logging.exception("[mapper]: Could not add user score.")
            return False

