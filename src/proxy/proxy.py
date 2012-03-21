'''
Created on Oct 31, 2011

@author: Arthur Valadares

Module that connects the front (client-side) of the proxy to the back (application-server-side). 
'''
# Intermediates messages between Front and Back
class Proxy():
    front = None
    back = None

class AbstractBack():
    def send_message_to_server(self,message,server=None):
        raise Exception('[Proxy]: Not implemented!')
    
    def broadcast_admins(self,message):
        raise Exception('[Proxy]: Not implemented!')
    
    def sticky_server(self):
        raise Exception('[Proxy]: Not implemented!')

    
class AbstractFront():
    def authorize_client(self, authclient, cuuid):
        raise Exception('[Proxy]: Not implemented!')
    
    def list_users(self):
        raise Exception('[Proxy]: Not implemented!')

    def send_message_to_client(self,message, clients):
        raise Exception('[Proxy]: Not implemented!')
        



