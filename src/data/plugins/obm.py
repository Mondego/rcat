'''
Created on May 18, 2012

@author: arthur
'''
from data.db.sqlalchemyconn import Host, ObjectManager as OBM
from sqlalchemy.ext.serializer import dumps
from threading import Thread, Lock
from tornado.ioloop import IOLoop
from tornado.web import asynchronous
import functools
import httplib
import json
import logging
import tornado.web
import urllib

obm = None
obm_otypes = {}
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
                
    def run(self):
        global obm_otypes
        try:
            oid = self.handler.get_argument("oid",None)
            otype_str = self.handler.get_argument("type",None)
            if otype_str:
                otype = obm_otypes[otype_str] 
            op = self.handler.get_argument("op",None)
            response = {'status':None,'result':None}
            
            if op == "post":
                immediate = self.handler.get_argument("immediate",False)
                propagate = self.handler.get_argument("propagate",True)
                obj = json.loads(self.handler.get_argument("obj"),None)
                if obj:
                    res = obm._post_local(otype,obj,oid,immediate,propagate)
                    response['status'] = 200
                    response['result'] = res
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(functools.partial(self.reply,jsonmsg))
                else:
                    IOLoop.instance().add_callback(self.failmsg)
            elif op == "put":
                obj = json.loads(self.handler.get_argument("obj"),None)
                res = obm._put_local(otype,obj,oid)
                if res:
                    response['status'] = 200
                    response['result'] = res
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(functools.partial(self.reply,jsonmsg))
                else:
                    IOLoop.instance().add_callback(self.failmsg)
                    raise Exception("[obm_handler]: Could not put object.")
            elif op == "get":
                obj = obm._get_local(otype,oid)
                logging.debug("[obm_handler]: Received get for object %s" % oid)
                if obj:
                    response['status'] = 200
                    response['result'] = json.dumps(obj)
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(functools.partial(self.reply,jsonmsg))
                    logging.debug("[obm_handler]: Sending get of object %s" % oid)
                else:
                    IOLoop.instance().add_callback(self.failmsg)
                    raise Exception("[obm_handler]: Could not find the object.")
            elif op == "relocate":
                newowner = self.handler.get_argument("no",None)
                obj = obm._relocate_to(otype,oid,newowner)
                if obj:
                    response['status'] = 200
                    jsonmsg = json.dumps(response)
                    IOLoop.instance().add_callback(functools.partial(self.reply,jsonmsg))
                else:
                    IOLoop.instance().add_callback(self.failmsg)
                    raise Exception("[obm_handler]: Could not relocate the object.")
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
        self.handler.write(message)
        self.handler.flush()
        self.handler.finish()
    
    def failmsg(self, message):
        def _write():
            if not message:
                # Template fail message
                fail = {'status':400,'resp':None}
                failmsg = json.dumps(fail)
            else:
                failmsg = message        
            self.handler.write(failmsg)
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
    object_locks = {}
    
    def __init__(self,datacon,rid_type=None):
        global obm
        obm = self
        self.myid = datacon.myid
        self.datacon = datacon
        self.cache = {}
        self.location = {}

    # Registers OBM in the database. Also prepares caching for all object types.        
    def register_node(self,adm,otypes):
        global obm_otypes
        for otype in otypes:
            obm_otypes[otype.__name__] = otype
            self.cache[otype] = {}
            self.location[otype] = {}
            self.object_locks[otype] = {}

        self.myhost = Host(adm, self.datacon.host)
        self.datacon.host = self.myhost
        ret = self.datacon.db.insert(self.myhost)
        if ret:
            return True
        else:
            return False
    
    def clear_cache(self,otypes):
        for otype in otypes:
            if otype in self.cache:
                del self.cache[otype]
            self.cache[otype] = {}
        return True
    
    def clear(self):
        return self.datacon.db.clear([OBM,Host])
        
    def find_all(self,otype):
        # TODO: There is still possible inconsistency, current frustrum must be subscribing to updates
        # maybe also we need timestamps..
        result = self.datacon.db.return_all(otype)
        return result
        
    def create_index(self,table,idxname):
        self.indexes[table][idxname] = {}
            
    def setowner(self,otype,oid,owner=None):
        if not owner:
            owner = self.myid
        try:
            obj,host = self.datacon.db.get_multiple([[OBM,oid],[Host,owner]])
            if not host:
                raise Exception("Host should exist in Host the table.")
            
            if not obj:
                obj = OBM(oid)
            obj.host = host
            self.datacon.db.insert(obj)
            self.location[otype][oid] = host
        except:
            logger.exception("[obm]: Failed to set owner in database.")
            return False
    
    def whereis(self,otype,oid):
        if oid in self.location[otype]:
            return self.location[otype][oid].hid
        else:
            return False # Not here
    
    """
    update_cache(self,otype,oid,hid): Checks if location of object is cached and if it matches the hid requested. Otherwise, update the cache. If it is still inconsistent,
    performs relocation.
    """
    def update_cache(self,otype,oid,hid,relocate=False):
        try:
            ret_object = self.datacon.db.get(OBM,oid,[OBM.host])
            if ret_object:
                # Found it, update the cache
                self.location[otype][oid] = ret_object.host
            else:
                # Didn't find it. Retrieve the data from database
                dbobj = self.datacon.db.get(otype,oid)
                if not dbobj:
                    # Object doesn't exist! Return an error
                    logger.error("[obm]: Object does not exist in database.")
                    return False
                else:
                    # Instantiate it here
                    self.setowner(otype, oid, hid)
                    self.cache[otype][oid] = dbobj
        except:
            logger.exception("[obm]: Error in update:")
            return False

        if relocate:
            if not self.location[otype][oid].hid == hid and hid == self.myhost.hid:
                # Object is supposed to be here, but its somewhere else. Means I need to first relocate it here!
                logger.warn("[obm]: Attempting to relocate object to correct place...")
                # Transfer from cached location to here:
                result = self.relocate(otype, oid, self.location[otype][oid].hid,self.myhost.hid)
                if result['status'] != 200:
                    logger.error("[obm]: Could not relocate to perform update.")
                    return False
        return True
            
        
    """
    PUT methods for OBM. (aka INSERT)
    otype: Type of object. Defined as a SQLAlchemy object
    newobj: New object to be inserted
    oid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, assumed to be a local insert.
    """
    def put(self,otype,newobj,oid,hid=None):
        if not hid or hid==self.myhost.hid:
            return self._put_local(otype, newobj, oid)
        else:
            return self._put_remote(otype, newobj, oid, hid)
            
    def _put_local(self,otype,newobj,oid):
        self.datacon.db.insert(newobj)
        self.setowner(otype,oid,newobj)
        self.cache[otype][oid] = newobj

        return self.cache[otype][oid]

    def _put_remote(self,otype,obj,oid,hid):
        remotehost = self.datacon.db.get(Host,hid)
        self.location[otype][oid] = remotehost
        res = self.send_request_owner(remotehost, otype.__name__, oid,"put", newobj=dumps(obj))
        logger.debug("[obm]: Inserting remotely at " + remotehost + " the object: " + str(obj))
        if res == "OK":
            return True
        else:
            logger.error(res)
         
    """
    POST methods for OBM. (aka UPDATE)
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    oid: Object identification. Commonly a UUID.
    tuples: Tuples to be updated
    hid: Host id of the intended destination. If none is given, a lookup is performed to find the host that has it (if any). If not yet assigned,
    assign it to the current instance and apply local update.
    immediate: If true, pushes to database immediate, otherwise, schedules for future update.
    propagate: Decides if message should be propagated to database at all. Otherwise, just stays cached.
    
    Methods:
    """
    def post(self,otype,oid,update_dict,hid=None,immediate=False, propagate=True):
        if hid==self.myhost.hid:
            # Update locally
            return self._post_local(otype, update_dict, oid, immediate, propagate)
        
        elif hid:
            # Update remotely
            return self._post_remote(otype, update_dict, oid, hid, immediate, propagate)

        else:
            # Find where it is and update it
            ret = self.datacon.db.get(OBM,oid,[OBM.host])
            if ret:
                # It is somewhere. If it is here, update local, otherwise update remote.
                if ret.host.hid != self.myhost.hid:
                    return self._post_remote(otype, update_dict, oid, ret.host.hid, immediate,propagate)
                elif ret.host.hid == self.myhost.hid:
                    return self._post_local(otype, update_dict, oid, immediate,propagate)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self._post_local(otype, update_dict, oid, immediate,propagate)
    
    def _post_local(self,otype,update_dict,oid,immediate=False, propagate=True):
        olock = self.get_lock(otype,oid)
        olock.acquire()
        
        ret_object = False
        
        try:
            if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != self.myhost.hid):
                # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
                ret_object = self.update_cache(otype, oid, self.myhost.hid)
                if not ret_object:
                    logger.error("[obm]: Could not retrieve object for post.")
                    ret_object = False
            try:
                obj = self.cache[otype][oid]
                obj.__dict__.update(update_dict)
                self.cache[otype][oid] = obj
                if propagate:
                    # Schedules update to be persisted.
                    if not immediate:
                        logger.debug("[obm]: Scheduling update: %s" % update_dict)
                        # TODO: Do update scheduling
                        ret_object = self.datacon.db.schedule_update(otype,oid,update_dict)
                        # ret = self.datacon.db.update(otype, oid, update_dict)
                        #ret = self.datacon.db.merge(obj)
                        # ret = self.datacon.db.insert_update(obj)
                    else:
                        # Critical message, needs immediate consistency
                        logger.debug("[obm]: Performing immediate update of %s." % obj)
                        #ret = self.datacon.db.update(otype, oid, update_dict)
                        #ret = self.datacon.db.merge(obj)
                        self.datacon.db.remove_scheduled_update(otype,oid)
                        ret_object = self.datacon.db.merge_insert(obj)
                            
            except KeyError:
                logger.exception("[obm]: Could not post locally. It is possible that the object is no longer here.")
        except:
            logger.exception("[obm]: Could not post locally.")
        finally:
            olock.release()
        
        return ret_object
    
    def _post_remote(self,otype,update_dict,oid,hid,immediate=False, propagate=True):
        if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, oid, hid)
            if not ret:
                logger.error("[obm]: Could not find object for post.")
                return False
                
        remotehost = self.datacon.db.get(Host,hid)
        post_params = []
        post_params.append("immediate="+str(immediate))
        post_params.append("propagate="+str(propagate))
        res = self.send_request_owner(remotehost, otype, oid, "post", update_values=update_dict,params=post_params)
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
    oid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, a lookup is performed to find the host that has it (if any). If not yet assigned,
    assign it to the current instance.
    """
    def get(self,otype,oid,hid=None):
        if hid == self.myhost.hid:
            return self._get_local(otype,oid)
        if hid and hid != self.myhost.hid:
            return self._get_remote(otype,oid,hid)
        else:
            # Find where it is and retrieve it
            ret = self.datacon.db.get(OBM,oid,[OBM.host])
            if ret:
                # It is somewhere. If it is here, get local, otherwise get remote.
                if ret.host.hid != self.myhost.hid:
                    return self._get_remote(otype, oid, ret.host.hid)
                elif ret.host.hid == self.myhost.hid:
                    return self._get_local(otype, oid)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self._get_local(otype, oid)
    
    """
    Same as get, but only checks in the cache. Returns false if not local.
    """
    def get_lazy(self,otype,oid):
        olock = self.get_lock(otype,oid)
        olock.acquire()
        
        ret_object = False
        
        try:        
            # If I own the object...
            if oid in self.location[otype] and self.location[otype][oid].hid != self.myhost.hid:
                #return it!
                ret_object = self.cache[otype][oid]
        except:
            logger.exception("[obm]: Failed to retrieve object.")
        finally:
            olock.release()
            
        return ret_object
                
    def _get_local(self,otype,oid):
        olock = self.get_lock(otype,oid)
        olock.acquire()
        
        ret_object = False
        try:
            if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != self.myhost.hid):
                # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
                ret = self.update_cache(otype, oid, self.myhost.hid)
                if not ret:
                    logger.error("[obm]: Could not retrieve object.")
                    
            ret_object = self.cache[otype][oid]
        except:
            logger.exception("[obm]: Failed to retrieve object.")
        finally:
            olock.release()
            
        return ret_object
        
        
    def _get_remote(self,otype,oid,hid):
        if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, oid, hid)
            if not ret:
                logger.error("[obm]: Could not retrieve data from %s." % (hid))
                return False
            
        res = self.send_request_owner(self.location[otype][oid], otype, oid, "get")
        if res['status'] == 200:
            logger.debug("[obm]: Remote get request. successful")
            self.cache[otype][oid] = res['result']
            ret = res['result']
        else:
            logger.error("[obm]: Failed to update remotely.")
            ret = False
        return ret
       
    """
    DELETE methods for OBM.
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    oid: Object identification. Commonly a UUID.
    hid: Host id of the intended destination. If none is given, a lookup is performed to find the host that has it (if any). If not yet assigned,
    assign it to the current instance.
    """
    def delete(self,otype,oid,hid=None):
        if hid == self.myhost.hid:
            return self._delete_local(otype,oid)
        if hid and hid != self.myhost.hid:
            return self._delete_remote(otype,oid,hid)
        else:
            # Find where it is and retrieve it
            ret = self.datacon.db.get(OBM,oid,[OBM.host])
            if ret:
                # It is somewhere. If it is here, delete local, otherwise delete remote.
                if ret.host.hid != self.myhost.hid:
                    return self._delete_remote(otype, oid, ret.host.hid)
                elif ret.host.hid == self.myhost.hid:
                    return self._delete_local(otype, oid)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self._delete_local(otype, oid)
    
    def _delete_local(self,otype,oid):
        if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != self.myhost.hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, oid, self.myhost.hid)
            if not ret:
                logger.error("[obm]: Could not retrieve object locally to delete.")
                return False
            
        #  I own the object! I'm cleared to delete! Clear myself as the owner first.
        self.datacon.db.delete(OBM,oid)
        self.datacon.db.delete(otype,oid)
        del self.location[otype][oid]
        if oid in self.cache[otype]:
            del self.cache[otype][oid]
        return True

    def _delete_remote(self,otype,oid,hid):
        if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, oid, self.myhost.hid)
            if not ret:
                logger.error("[obm]: Could not find object to delete.")
                return False
            
        res = self.send_request_owner(self.location[otype][oid], otype, oid, "delete")
        if res['status'] == 200:
            logger.debug("[obm]: Remote delete request. successful")
            if oid in self.cache[otype]:
                del self.cache[otype][oid]
            ret = True
        else:
            logger.error("[obm]: Failed to delete remotely.")
            ret = False
        return ret

    """
    RELOCATE methods for OBM.
    Arguments:
    otype: Type of object. Defined as a SQLAlchemy object
    oid: Object identification. Commonly a UUID.
    source: Host id of the source of the relocation. If none is given, a lookup is performed to find the host that has it (if any).
    dest: Host id of the intended destination for the object. 
    
    Methods:
    _relocate_from(self,otype,oid,source): Relocate object `oid` of type `otype` from `source` to here.
    _relocate_to(self,otype,oid,dest): Relocate object `oid` of type `otype` from here to destination `dest`.
    """  
    def relocate(self,otype,oid,source=None,dest=None):
        if not dest:
            # Must have a destination
            return False
        if source == self.myhost.hid:
            # If source is here, relocate to destination 
            return self._relocate_to(otype,oid,dest)
        if dest == self.myhost.hid:
            # If destination is here, relocate from source
            return self._relocate_from(otype,oid,source)
        elif not source and (not dest or dest == self.myhost.hid):
            # Want to transfer object here, but don't know where it is.
            ret = self.datacon.db.get(OBM,oid,[OBM.host])
            if ret:
                # It is somewhere. If it is here, just return the value, otherwise perform relocation to here.
                if ret.host.hid == self.myhost.hid:
                    return self.get(otype,oid,self.myhost.hid)
                elif ret.host.hid != self.myhost.hid:
                    return self._relocate_from(otype, oid, ret.host.hid)
            else:
                # It has not yet been assigned. Might as well assign it here.
                return self.get(otype,oid,self.myhost.hid)
        else:
            # TODO: Thomas told me not to!
            logger.error("[obm]: Destination or source must be local node.")
            return False
    
    def _relocate_from(self,otype,oid,source):
        olock = self.get_lock(otype,oid)
        olock.acquire()
        
        ret_object = False
        try:
            if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != source):
                # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
                ret = self.update_cache(otype, oid, source, False)
                if not ret:
                    logger.error("[obm]: Could not relocate object because object does not exist.")
                    ret_object = False
            
            # If the relocation already happened, just return True    
            if self.location[otype][oid].hid == self.myhost.hid:
                ret_object = True
            else:
                # Either object is in the source, or the actual location of the object has been updated. Either way, attempting to relocate.
                result = self.send_request_owner(self.location[otype][oid],otype,oid,"relocate")
                count = 0        
                while (result['status'] != 200 and count < 10 and self.location[otype][oid].hid != self.myhost.hid):
                    # Failed to retrieve it. Update cache and try again.
                    count+=1
                    ret = self.update_cache(otype,oid,source,False)
                    
                    if not ret:
                        logger.error("[obm]: Could not relocate object because object does not exist.")
                    else:
                        result = self.send_request_owner(self.location[otype][oid],otype,oid,"relocate")
                        
                if count == 10:
                    logger.error("[obm]: Too many attempts to relocate. Giving up!")
                elif (result['status'] == 200):
                    ret_object = result['result']
                
                if ret_object:
                    # All went well. Set location cache and object cache, and return the state of the relocated data.
                    self.cache[otype][oid] = self.datacon.db.get(otype,oid)
                    logger.debug("[obm]: Relocated object %s, added to cache " % self.cache[otype][oid])
                    self.location[otype][oid] = self.myhost
        except:
            logger.error("[obm]: Exception relocating %s from %s" % (oid,source))
        finally:
            olock.release()
        return ret_object
    
    def _relocate_to(self,otype,oid,dest):
        olock = self.get_lock(otype,oid)
        olock.acquire()
        ret_object = False
        
        if oid not in self.location[otype] or (oid in self.location[otype] and self.location[otype][oid].hid != self.myhost.hid):
            # Either I dont know where it is or my cache thinks its somewhere else. Update cache!
            ret = self.update_cache(otype, oid, self.myhost.hid,False)
            if (not ret or (self.location[otype][oid].hid != self.myhost.hid)):
                logger.warn("[obm]: Could not relocate object because I could not own it. Maybe it moved.")
                self.object_locks[otype][oid].release()
                return False
            
        # Object is surely located here. Proceed with the relocation.
        # TODO: Lock this method
        logger.debug("[obm]: Relocating %s %s to %s" % (otype,oid,dest))
        try:
            if oid in self.cache[otype]:
                self.datacon.db._obm_replace_host(oid,dest)
                self.datacon.db.merge(self.cache[otype][oid])
                ret_object = self.cache[otype][oid] 
                del self.cache[otype][oid]
                self.location[otype][oid] = self.datacon.db.get(Host,dest)
                self.datacon.db.remove_scheduled_update(otype,oid)
            else:
                logger.debug("[obm]: Object is no longer here. Maybe it already has transferred.")
                ret_object = False
        except:
            logger.exception("[obm]: Error relocating:")
            ret_object = False
        finally:
            olock.release()
            
        return ret_object
     
     
    def get_lock(self,otype,oid):
        if not oid in self.object_locks[otype]:
            self.object_locks[otype][oid] = Lock()
        return self.object_locks[otype][oid]
    """
    send_request_owner(self,host,otype,oid,op,newobj,update_values,params): Sends message to authoritative owner of object with an obm command.
    host: Host object, containing address to request object
    otype: Type of object being requested.
    oid: ID of the object being requested
    newobj: Object (SQL ALchemy) that is to be inserted, for put operations
    update_values: Dictionary of items to update an object with. 
    params: Extra parameters. Currently used only for the immediate flag in update.
    TODO: Make all parameters dictionary?
    """    
    def send_request_owner(self,host_obj,otype,oid,op,newobj=None,update_values={},params=[]):
        host,port = host_obj.address.split(':')
        cmd = ''
        if op == "post":
            cmd = "&op=post&obj=" + urllib.quote(json.dumps(update_values))
        elif op == "select":
            cmd = "&op=get"
        elif op == "relocate":
            cmd = "&op=relocate&no=" + self.myhost.hid
        elif op == "put":
            cmd = "&op=put&obj=" + urllib.quote(newobj)
        
        if params:
            cmd += '&' + '&'.join([param for param in params]) 
        try:
            conn = httplib.HTTPConnection(host,port,timeout=4)
            request_string = "/obm?oid=%s&type=%s%s" % (oid,otype.__name__,cmd) 
            logging.debug("[obm]: Sending request to %s. Request line:%s" % (host_obj.address, request_string))
            conn.request("GET",request_string)
            resp = conn.getresponse()
            if resp.status == 200:
                res = json.loads(resp.read())
                return {'status':200, 'result':res}
            else:
                logging.error("[obm]: Received a bad status from HTTP.")
                return {'status':resp.status, 'result':None}
        except:
            logger.exception("[obm]: Failed send requesting to owner:")
            return {'status':400, 'result':None}
