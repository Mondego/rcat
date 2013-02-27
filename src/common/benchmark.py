'''
Created on Jan 29, 2013

@author: Arthur Valadares
'''
from threading import Thread
import csv
import os
import random
import resource
import time

class ResourceMonitor():
    
    def __init__(self, fname, interval=5):
        self.interval = interval
        self.last_timestamp = 0
        # for each benchmarked value, store its C-struct name, human-readable name, and value at the previous step
        # cf http://linux.die.net/man/2/getrusage  
        self.benchmarked_values = [['ru_utime', 'userTime', 0],  # in seconds
                                   ['ru_stime', 'systemTime', 0],  # in seconds
                                   ['ru_maxrss', 'max resident set', 0],
                                   ['ru_ixrss', 'shared mem', 0],
                                   ['ru_idrss', 'unshared mem', 0],
                                   ['ru_isrss', 'unshared stack', 0],
                                   ['ru_minflt', 'page faults w/o IO', 0],
                                   ['ru_majflt', 'page faults with IO', 0],
                                   ['ru_nswap', 'swap outs', 0],
                                   ['ru_inblock', 'block input ops', 0],
                                   ['ru_oublock', 'block output ops', 0],
                                   ['ru_nvcsw', 'v context switches', 0],
                                   ['ru_nivcsw', 'iv context switches', 0]]
        if os.path.exists(fname):
            name_split = fname.split('.')
            if len(name_split) > 1:
                prefix = name_split[len(name_split) - 2]
            i = 0
            while (os.path.exists(fname)):
                test_prefix = prefix
                test_prefix += str(i)
                i += 1
                name_split[len(name_split) - 2] = test_prefix
                fname = ""
                for name in name_split:
                    fname += name + '.'
            
        self.fname = fname
        self.file = open(self.fname, 'w', 0)
        self.writer = csv.writer(self.file)
        header = ['humanTime', 'elapsedTime'] + [tup[1] for tup in self.benchmarked_values]
#        firstline = ['time', 'user time', 'system time', 'max resident set', 'shared mem', 'unshared mem', 'unshared stack', 'page faults w/ IO', 'page faults w IO',
#                     'swap outs', 'block input ops', 'block output ops', 'msgs sent', 'msgs received', 'signals rcvd', 'v context switches', 'iv context switches']
        self.writer.writerow(header)
        self.file.close()
        
    def collect(self):
        while (self.collecting):
            now = time.time()
            elapsed_time = now - self.last_timestamp  # in seconds
            resources = resource.getrusage(resource.RUSAGE_SELF)
            if self.last_timestamp:  # dont log deltas for the first step
                bm_values = [getattr(resources, tup[0]) - tup[2] for tup in self.benchmarked_values] 
                # write values to file
                self.file = open(self.fname, 'a', 0)
                self.writer = csv.writer(self.file)
                usage = []
                usage.append(time.strftime("%H:%M:%S", time.localtime()))  # human-readble time
                usage.append(elapsed_time)
                usage.extend(bm_values)
                self.writer.writerow(usage)
                self.file.close()
            #  in any case, set the benchmark and time measures to their current value
            self.last_timestamp = now
            for tup in self.benchmarked_values:
                tup[2] = getattr(resources, tup[0])
            # sleep until next step
            time.sleep(self.interval)
        
    def stop(self):
        self.collecting = False
        
    def start(self):
        self.collecting = True
        self.run = Thread(target=self.collect)
        self.run.daemon = True
        self.run.start()
        
if __name__ == "__main__":
    resmon = ResourceMonitor('test.csv')
    resmon.start()
    raw_input("Press Enter to end...")
    resmon.stop()
