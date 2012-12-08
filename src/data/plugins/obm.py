'''
Created on May 18, 2012

@author: arthur
'''
from data.db.sqlalchemyconn import ObjectManager, Host
from examples.jigsaw.server_alchemy.mapper.dbobjects import Piece
from multiprocessing.pool import ThreadPool
from sqlalchemy.orm.exc import NoResultFound
from threading import Thread
from tornado.ioloop import IOLoop
from tornado.web import asynchronous
import httplib
import json
import logging
import tornado.web
import urllib
from sqlalchemy.ext.serializer import loads, dumps

obm = None
logger = logging.getLogger()

class OBMHandler(tornado.web.RequestHandler):
    
    def initialize(self):
        global pubsubs
        pubsubs = {}
        
    @asynchronous
    def get(self):
        # TODO: Worker threads to save hassle of starting threads
        OBMParser(self).start()
        

class OBMParser(Thread):
    failmsg = None
    
    def __init__(self,handler):
        Thread.__init__(self)
        self.daemon = True
        self.handler = handler
        
        # Template fail message
        fail = {'status':400,'resp':None}
        self.failmsg = json.dumps(fail)
                
    def run(self):
        try:
            rid = self.handler.get_argument("rid",None)
            otype = self.handler.get_argument("type",None)
            op = self.handler.get_argument("op",None)
            response = {'status':None,'result':None}
            
            if op == "post":
                immediate = self.handler.get_argument("immediate",False)
                obj = loads(self.handler.get_argument("obj"),None)
                if obj:
                    res = obm.post_local(otype,obj,rid,immediate)
                    response['status'] = 200
                    response['result'] = res
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(jsonmsg)
                else:
                    IOLoop.instance().add_callback(self.failmsg)
            elif op == "put":
                obj = loads(self.handler.get_argument("obj"),None)
                res = obm.put_local(otype,obj,rid)
                if res:
                    response['status'] = 200
                    response['result'] = res
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(jsonmsg)
                else:
                    IOLoop.instance().add_callback(self.failmsg)
            elif op == "get":
                obj = obm.get_local(otype,rid)
                if obj:
                    response['status'] = 200
                    response['result'] = dumps(obj)
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(jsonmsg)
            elif op == "relocate":
                newowner = self.handler.get_argument("no",None)
                obj = obm.relocate_to(otype,rid,newowner)
                if obj:
                    response['status'] = 200
                    response['result'] = dumps(obj)
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(self.reply(jsonmsg))
            elif op == "subscribe":
                ip =  self.handler.request.remote_ip
                port = self.handler.get_argument("port",None)
                interests = json.loads(self.handler.get_argument("interests",None))
                loc = (ip,port)
                if pubsubs:
                    pubsubs[otype].add_subscriber(loc,interests)
        except:
            logger.exception("[obmparser]: Error parsing request:") 
    
    def reply(self,message):
        def _write():
            self.handler.write(message)
            self.handler.flush()
            self.handler.finish()
        return _write
    
    def on_complete_all(self):
        self.handler.finish()
        
            
class ObjectManager():
    datacon = None
    myid = None
    myhost = None
    host = None
    cache = {}
    location = {}
    ridnames = {}
    indexes = {}
    columns = {}
    autoinc = {}
    
    def __init__(self,datacon,rid_type=None):
        global obm
        obm = self
        self.myid = datacon.myid
        self.myhost = datacon.host
        self.datacon = datacon
        self.cache = {}
        self.location = {}

    # Registers OBM in the database. Also prepares caching for all object types.        
    def register_node(self,adm,otypes):
        self.host = Host(adm, self.datacon.host)
        
        for otype in otypes:
            self.cache[otype] = {}
            self.location[otype] = {}
    
    def clear(self,table):
        return self.datacon.db.clear([ObjectManager,Host])
        
    def find_all(self,otype):
        # TODO: There is still possible inconsistency, current frustrum must be subscribing to updates
        # maybe also we need timestamps..
        result = self.datacon.db.return_all(otype)
        return result
        
    def create_index(self,table,idxname):
        self.indexes[table][idxname] = {}
            
    def setowner(self,otype,rid,owner=None):
        if not owner:
            owner = self.myid
        try:
            obj,host = self.datacon.db.get([[ObjectManager,rid],[Host,owner]])
            obj.host = host
            self.datacon.db.insert_update(obj)
            self.location[otype][rid] = host
        except Exception, e:
            logger.exception("[obm]: Failed to set owner in database.")
            return False
    
    def whereis(self,otype,rid):
        return self.location[otype][rid]
    
    """
    update_cache(self,otype,rid,hid): Checks if location of object is cached and if it matches the hid requested. Otherwise, update the cache. If it is still inconsistent,
    performs relocation.
    """
    def update_cache(self,otype,rid,hid,relocate=False):
        try:
            ret_object = self.datacon.db.get(ObjectManager,rid)
            if ret_object:
                # Found it, update the cache
                self.location[otype][rid] = ret_object.host
            else:
                # Didn't find it. Retrieve the data from database
                dbobj = self.datacon.db.get(otype,rid)
                if not dbobj:
                    # Object doesn't exist! Return an error
                    logger.error("[obm]: Object does not exist in database.")
                    return False
                else:
                    # Instantiate it here
                    self.setowner(otype, rid, hid)
        except:
            logging.exception("[obm]: Error in update:")

        if relocate:
            if not self.location[otype][rid].hid == hid and hid == self.myhost.hid:
                # Object is supposed to be here, but its somewhere else. Means I need to first relocate it here!
                logging.warn("[obm]: Attempting to relocate object to correct place...")
                # Transfer from cached location to here:
                result = self.relocate(otype, rid, self.location[otype][rid].hid,self.myhost.hid)
                if result['status'] != 200:
                    logger.error("[obm]: Could not relocate to perform update.")
                    return False
        return True
            
        
    """
    PUT methods for OBM. (aka INSERT)
    otype: Type of object. Defined as a SQLAlchemy object
    newobj: New object to be inserted
    rid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, assumed to be a local insert.
    """
    def put(self,otype,newobj,rid,hid=None):
        if not hid or hid==self.myhost.hid:
            return self.put_local(otype, newobj, rid)
        else:
            return self.put_remote(otype, newobj, rid, hid)
            
    def put_local(self,otype,newobj,rid):
        self.datacon.db.insert_update(newobj)
        self.setowner(otype,rid,newobj)
        self.cache[otype][rid] = newobj

        return self.cache[otype][rid]

    def put_remote(self,otype,obj,rid,hid):
        remotehost = self.datacon.db.get(Host,hid)
        self.location[otype][rid] = remotehost
        res = self.send_request_owner(remotehost, otype.__name__, rid, "put",dumps(obj))
        logger.debug("[obm]: Inserting remotely at " + remotehost + " the object: " + str(obj))
        if res == "OK":
            return True
        else:
            logger.error(res)
         
    """
    POST methods for OBM. (aka UPDATE)
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    obj: Object to be updated.
    rid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, a lookup is performed to find the host that has it (if any). If not yet assigned,
    assign it to the current instance and apply local update.
    immediate: If true, pushes to database immediate, otherwise, schedules for future update.
    
    Methods:
    """
    def post(self,otype,rid,tuples,hid=None,immediate=False):
        if hid==self.myhost.hid:
            # Update locally
            return self.post_local(otype, tuples, rid, immediate)
        
        elif hid:
            # Update remotely
            return self.post_remote(otype, tuples, rid, hid, immediate)

        else:
            # Find where it is and update it
            ret = self.datacon.db.get(ObjectManager,rid)
            if ret:
                # It is somewhere. If it is here, update local, otherwise update remote.
                if ret.host.hid != self.myhost.hid:
                    return self.post_remote(otype, tuples, rid, ret.host.hid, immediate)
                elif ret.host.hid == self.myhost.hid:
                    return self.post_local(otype, tuples, rid, immediate)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self.post_local(otype, tuples, rid, immediate)
    
    def post_local(self,otype,tuples,rid,immediate=False):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != self.myhost.hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, self.myhost.hid)
            if not ret:
                logger.error("[obm]: Could not retrieve object for post.")
                return False

        # Schedules update to be persisted.
        if not immediate:
            logger.debug("[obm]: Scheduling update.")
            ret = self.datacon.db.schedule_update(tuples)
        else:
            # Critical message, needs immediate consistency
            logger.debug("[obm]: Performing immediate update.")
            ret = self.datacon.db.update(otype,rid,tuples)
        return ret
    
    def post_remote(self,otype,obj,rid,hid,immediate=False):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, hid)
            if not ret:
                logger.error("[obm]: Could not find object for post.")
                return False
                
        remotehost = self.datacon.db.get(Host,hid)
        res = self.send_request_owner(remotehost, otype, rid, "post",dumps(obj),params="immediate="+str(immediate))
        if res['status'] == 200:
            logger.debug("[obm]: Remote update request.")
            ret = True
        else:
            logger.error("[obm]: Failed to update remotely.")
            ret = False
        return ret
    
    
    """
    GET methods for OBM. (aka SELECT)
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    rid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, a lookup is performed to find the host that has it (if any). If not yet assigned,
    assign it to the current instance.
    """
    def get(self,otype,rid,hid=None):
        if hid == self.myhost.hid:
            return self.get_local(otype,rid)
        if hid and hid != self.myhost.hid:
            return self.get_remote(otype,rid,hid)
        else:
            # Find where it is and retrieve it
            ret = self.datacon.db.get(ObjectManager,rid)
            if ret:
                # It is somewhere. If it is here, get local, otherwise get remote.
                if ret.host.hid != self.myhost.hid:
                    return self.get_remote(otype, rid, ret.host.hid)
                elif ret.host.hid == self.myhost.hid:
                    return self.get_local(otype, rid)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self.get_local(otype, rid)
                
    def get_local(self,otype,rid):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != self.myhost.hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, self.myhost.hid)
            if not ret:
                logger.error("[obm]: Could not retrieve object.")
                return False
            
        return self.cache[otype][rid]

        
    def get_remote(self,otype,rid,hid):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, hid)
            if not ret:
                logger.error("[obm]: Could not retrieve data from %s." % (hid))
                return False
            
        res = self.send_request_owner(self.location[otype][rid], otype, rid, "get")
        if res['status'] == 200:
            logger.debug("[obm]: Remote get request. successful")
            self.cache[otype][rid] = res['result']
            ret = res['result']
        else:
            logger.error("[obm]: Failed to update remotely.")
            ret = False
        return ret
       
    """
    DELETE methods for OBM.
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    rid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, a lookup is performed to find the host that has it (if any). If not yet assigned,
    assign it to the current instance.
    """
    def delete(self,otype,rid,hid=None):
        if hid == self.myhost.hid:
            return self.delete_local(otype,rid)
        if hid and hid != self.myhost.hid:
            return self.delete_remote(otype,rid,hid)
        else:
            # Find where it is and retrieve it
            ret = self.datacon.db.get(ObjectManager,rid)
            if ret:
                # It is somewhere. If it is here, delete local, otherwise delete remote.
                if ret.host.hid != self.myhost.hid:
                    return self.delete_remote(otype, rid, ret.host.hid)
                elif ret.host.hid == self.myhost.hid:
                    return self.delete_local(otype, rid)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self.delete_local(otype, rid)
    
    def delete_local(self,otype,rid):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != self.myhost.hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, self.myhost.hid)
            if not ret:
                logger.error("[obm]: Could not retrieve object locally to delete.")
                return False
            
        #  I own the object! I'm cleared to delete! Clear myself as the owner first.
        self.datacon.db.delete(ObjectManager,rid)
        self.datacon.db.delete(otype,rid)
        del self.location[otype][rid]
        if rid in self.cache[otype]:
            del self.cache[otype][rid]
        return True

    def delete_remote(self,otype,rid,hid):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, self.myhost.hid)
            if not ret:
                logger.error("[obm]: Could not find object to delete.")
                return False
            
        res = self.send_request_owner(self.location[otype][rid], otype, rid, "delete")
        if res['status'] == 200:
            logger.debug("[obm]: Remote delete request. successful")
            if rid in self.cache[otype]:
                del self.cache[otype][rid]
            ret = True
        else:
            logger.error("[obm]: Failed to delete remotely.")
            ret = False
        return ret

    """
    RELOCATE methods for OBM.
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    rid: Object identification. Commonly a UUID.
    source: Host id of the source of the relocation. If none is given, a lookup is performed to find the host that has it (if any).
    dest: Host id of the intended destination for the object. 
    
    Methods:
    relocate_from(self,otype,rid,source): Relocate object `rid` of type `otype` from `source` to here.
    relocate_to(self,otype,rid,dest): Relocate object `rid` of type `otype` from here to destination `dest`.
    """  
    def relocate(self,otype,rid,source=None,dest=None):
        if not dest:
            # Must have a destination
            return False
        if source == self.myhost.hid:
            # If source is here, relocate to destination 
            return self.relocate_to(otype,rid,dest)
        if dest == self.myhost.hid:
            # If destination is here, relocate from source
            return self.relocate_from(otype,rid,source)
        elif not source and (not dest or dest == self.myhost.hid):
            # Want to transfer object here, but don't know where it is.
            ret = self.datacon.db.get(ObjectManager,rid)
            if ret:
                # It is somewhere. If it is here, just return the value, otherwise perform relocation to here.
                if ret.host.hid == self.myhost.hid:
                    return self.get(otype,rid,self.myhost.hid)
                elif ret.host.hid != self.myhost.hid:
                    return self.relocate_from(otype, rid, ret.host.hid)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self.get(otype,rid,self.myhost.hid)
        else:
            # TODO: Thomas told me not to!
            logger.error("[obm]: Destination or source must be local node.")
            return False
    
    def relocate_from(self,otype,rid,source):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != source):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, source, False)
            if not ret:
                logger.error("[obm]: Could not relocate object because object does not exist.")
                return False
        
        # If the relocation already happened, just return True    
        if self.location[otype][rid].hid == self.myhost.hid:
            return True
        
        # Either object is in the source, or the actual location of the object has been updated. Either way, attempting to relocate.
        result = self.send_request_owner(self.location[otype][rid],otype,rid,"relocate")
        count = 0        
        while (result['status'] != 200 and count < 10 and self.location[otype][rid].hid != self.myhost.hid):
            # Failed to retrieve it. Update cache and try again.
            count+=1
            ret = self.update_cache(otype,rid,source,False)
            
            if not ret:
                logger.error("[obm]: Could not relocate object because object does not exist.")
                return False
            else:
                result = self.send_request_owner(self.location[otype][rid],otype,rid,"relocate")
                
        if count == 10:
            logger.error("[obm]: Too many attempts to relocate. Giving up!")
            return False
        
        # All went well. Set location cache and object cache, and return the state of the relocated data.
        self.cache[otype][rid] = result['result']
        self.location[otype][rid] = self.myhost.hid
        
        return result['result']
    
    def relocate_to(self,otype,rid,dest):
        if rid not in self.location[otype] or (rid in self.location[otype] and self.location[otype][rid].hid != self.myhost.hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, rid, self.myhost.hid,False)
            if (not ret or (self.location[otype][rid].hid != self.myhost.hid)):
                logger.warn("[obm]: Could not relocate object because I could not own it. Maybe it moved.")
                return False
            
        # Object is surely located here. Proceed with the relocation.
        # TODO: Lock this method
        try:
            obj = self.datacon.db.get(ObjectManager,rid)
            newhost = self.datacon.db.get(Host,dest)
            obj.host = newhost
            self.datacon.db.insert_update(obj)
        except:
            logger.exception("[obm]: Error relocating:")
        
        return self.cache[otype][rid]
        
    """
    send_request_owner(self,host,table,RID,name,update_value): Sends message to authoritative owner of object with an obm command.
    """    
    def send_request_owner(self,obj_location,otype,rid,op,obj=None,params=[]):
        host,port = obj_location.split(':')
        if op == "post":
            cmd = "&op=post&obj=" + urllib.quote(obj)
        elif op == "select":
            cmd = "&op=get"
        elif op == "relocate":
            cmd = "&op=relocate&no=" + self.myhost.hid
        elif op == "put":
            cmd = "&op=put&obj=" + urllib.quote(obj)
        
        if params:
            cmd += '&' + '&'.join([param for param in params]) 
        try:
            conn = httplib.HTTPConnection(host,port,timeout=4)
            logging.debug("[obm]: Sending request to " + obj_location)
            conn.request("GET", "/obm?rid=%s&type=%s%s" % (rid,otype,cmd))
            resp = conn.getresponse()
            if resp.status == 200:
                res = resp.read()
                return json.loads(res)
            else:
                logging.error("[obm]: Received a bad status from HTTP.")
                return resp.status
        except:
            logger.exception("[obm]: Failed send requesting to owner:")
