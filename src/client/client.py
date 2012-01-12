'''
Created on Oct 29, 2011

@author: tdebeauv
'''


import httplib
import urllib

myURL = 'localhost:8888'
conn = httplib.HTTPConnection(myURL)
params = urllib.urlencode({'body':'hello'})
print params
conn.request('POST', '/a/message/new', params)
res = conn.getresponse()

#I am only interested in 200 OK response, anything else can be ignored
if res.status == 200:
    data = res.read()
    allheaders = res.getheaders()
    print 'data: ', data 
    for header in allheaders:
        print '  ', header[0], ':', header[1]
else:
    print 'POST failed on ', myURL, ', reason: ', res.reason, ', status: ', res.status
