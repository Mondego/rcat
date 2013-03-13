"""
File: global.py
Description: File containing global variable definitions
"""

"""
Message Types
"""
class MESSAGE_TYPE:
    CONNECT=1
    ACCEPTED=2
    WEBSOCKET=3
    HTTP=4

class DEBUG:
    OFF=0
    ON=1
    
class PROXY_DISTRIBUTION:
    ROUNDROBIN=0
    STICKY=1