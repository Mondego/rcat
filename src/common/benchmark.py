'''
Created on Jan 29, 2013

@author: Arthur Valadares
'''
from threading import Thread
import csv
import resource
import time

class ResourceMonitor():
    
    def __init__(self,fname,interval=5):
        self.interval = interval
        self.fname = fname
        self.file = open(self.fname, 'w', 0)
        self.writer = csv.writer(self.file)
        firstline = ['time','user time','system time','max resident set','shared mem','unshared mem','unshared stack','page faults w/ IO', 'page faults w IO',
                     'swap outs','block input ops','block output ops','msgs sent','msgs received','signals rcvd','v context switches','iv context switches']
        self.writer.writerow(firstline)
        self.file.close()
        
    def collect(self):
        while (self.collecting):
            self.file = open(self.fname, 'a', 0)
            self.writer = csv.writer(self.file)
            usage = []
            usage.append(time.strftime("%H:%M:%S", time.localtime()))
            usage.extend(list(resource.getrusage(resource.RUSAGE_SELF)))
            self.writer.writerow(usage)
            self.file.close()
            time.sleep(self.interval)
        
    def stop(self):
        self.collecting = False
        
    def start(self):
        self.collecting = True
        self.run = Thread(target=self.collect)
        self.run.start()
        
if __name__ == "__main__":
    resmon = ResourceMonitor('test.csv')
    resmon.start()
    raw_input("Press Enter to end...")
    resmon.stop()