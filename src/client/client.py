'''
Created on Oct 29, 2011

@author: tdebeauv
'''

#
#import urllib
#
#url = 'http://localhost:8888'
#u = urllib.urlopen(url)
## u is a file-like object
#data = u.read()
#print data

import httplib

myURL = 'localhost:8888'
conn = httplib.HTTPConnection(myURL)
conn.request('GET', '/')
res = conn.getresponse()
#I am only interested in 200 OK response, anything else can be ignored
if res.status != 200:
    print 'GET faield on ', myURL, ', reason: ', res.reason, ', status: ', res.status
else:
    data = res.read()
    allheaders = res.getheaders()
    print 'data: ', data 
    for header in allheaders:
        print '  ', header[0], ':', header[1]  

