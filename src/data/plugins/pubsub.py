import SocketServer
import socket
import json

tables = None

class PubSub():
    def __init__(self,tbls):
        global tables
        tables = tbls    

class PubSubUpdateHandler(SocketServer.BaseRequestHandler):
    """
    This class works similar to the TCP handler class, except that
    self.request consists of a pair of data and client socket, and since
    there is no connection the client address must be given explicitly
    when sending data back via sendto().
    """    
    def handle(self):
        print self.request
        data = json.loads(self.request[0].strip())
        tbl = data["tbl"]
        rid = data["rid"]
        op = data["op"]
        if op == "insert":
            tables[tbl][rid].append(data["data"])
        elif op == "update":
            if "row" in data:
                row = int(data["row"])
                tables[tbl][rid][row] = data["data"]
            else:
                tables[tbl][rid] = data["data"]
        
        #socket = self.request[1]
        #socket.sendto("OK", self.client_address)
        
        """
        print "{} wrote:".format(self.client_address[0])
        print data
        socket.sendto(data.upper(), self.client_address)
        """

class PubSubUpdateSender():
    subscribers = []
    table = ""
    sock = None
    
    def __init__(self,name):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def add_subscriber(self,location,interests):
        subscriber = {}
        subscriber["location"] = location
        subscriber["interests"] = interests
        self.subscribers.append(subscriber)

    # TODO: Increase performance, improve algorithm    
    def send(self, rid, updated_dict):
        msg = {}
        msg["rid"] = rid
        msg["tbl"] = self.table
        msg["data"] = updated_dict # Dictionary with updated values only
        message = json.dumps(msg)
         
        for subscriber in self.subscribers:
            if subscriber["interests"]:
                for interest in subscriber["interests"]:
                    if interest in updated_dict:
                        self.sock.sendto(json.dumps(message) + "\n", subscriber["location"])
                        break
            else:
                self.sock.sendto(json.dumps(message) + "\n", subscriber["location"])
                