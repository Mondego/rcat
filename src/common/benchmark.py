'''
Created on Jan 29, 2013

@author: Arthur Valadares
'''
from threading import Thread
import csv
import os
import resource
import time

class ResourceMonitor():
    
    def __init__(self, fname, interval=5, metrics=[]):
        """
        interval is in seconds
        metrics is a list of couples: ('metricName', callbackToGetMetricFrom) 
        """
        
        self.interval = interval
        self.last_timestamp = 0 # when did i last measure
        # for each benchmarked value, store its C-struct name, human-readable name, and value at the previous step
        # cf http://linux.die.net/man/2/getrusage
        self.benchmarked_values = [['ru_utime', 'userCpuRatio', 0],  # in seconds
                                   ['ru_stime', 'systemCpuRatio', 0],  # in seconds
                                   ['ru_maxrss', 'maxResidentSetPerSec', 0],
                                   ['ru_minflt', 'pageFaultsWithoutIOPerSec', 0],
                                   ['ru_majflt', 'pageFaultsWithIOPerSec', 0],
                                   #['ru_nswap', 'swap outs per sec', 0],
                                   ['ru_inblock', 'blockInputOpsPerSec', 0],
                                   ['ru_oublock', 'blockOutputOpsPerSec', 0],
                                   ['ru_nvcsw', 'vContextSwitchesPerSec', 0],
                                   ['ru_nivcsw', 'ivContextSwitchesPerSec', 0]]
        # if the file exists, pick a new name
        # TODO: bug: this results in file names like "proxy_resmon.csv."
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
        header = ['humanTime', 'timestamp']
        header += [metric[0] for metric in metrics]
        self.metrics = metrics
        header += [tup[1] for tup in self.benchmarked_values]
        self.writer.writerow(header)
        self.file.close()
        
    def collect(self):
        while (self.collecting):
            now = time.time()
            elapsed_time = now - self.last_timestamp  # in seconds
            resources = resource.getrusage(resource.RUSAGE_SELF)
            if self.last_timestamp:  # dont log deltas for the first step
                # get all needed metrics and usage values
                custom_metrics_values = [metric[1]() for metric in self.metrics]
                bm_values = [(getattr(resources, tup[0]) - tup[2])/elapsed_time for tup in self.benchmarked_values]
                # write values to file
                self.file = open(self.fname, 'a', 0)
                self.writer = csv.writer(self.file)
                usage = []
                usage.append(time.strftime("%H:%M:%S", time.localtime()))  # human-readble time
                usage.append(now)
                usage.extend(custom_metrics_values)
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
