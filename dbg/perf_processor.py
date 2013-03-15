import csv
import os
from math import sqrt
import sys

run_folder = sys.argv[1] # example: results/trialRun
if run_folder.endswith('/'):
    run_folder = run_folder[:-1] # remove trailing '/'
run_name = run_folder.split('/')[-1]

###################  tools

# from http://stackoverflow.com/a/7464107/856897
def percentile(l, P):
    """
    Find the percentile of a list of values
    @parameter l - A list of values.  l must be sorted.
    @parameter P - A float value from 0.0 to 1.0
    @return - The percentile of the values.
    """
    n = int(round(P * len(l) + 0.5))
    try:
        return l[n - 1]
    except IndexError:
        pass

# from http://stackoverflow.com/a/1175084/856897
def get_mean_stdev(l):
    """ Return the mean and stdev of a list of numbers """
    n = len(l)
    sum_x2 = 0
    sum_x = 0
    for x in l:
        sum_x2 += x * x
        sum_x += x
    mean = sum_x / n
    stdev = sqrt((sum_x2 / n) - mean * mean)
    return mean, stdev


def get_stats(l):
    """ return mean, stdev, and 99th percentile of a list """
    if l:
        mean, stdev = get_mean_stdev(l)
        l.sort()
        l_99 = percentile(l, .99)
    else:
        mean, stdev = '', ''
        l_99 = ''
    return mean, stdev, l_99


#####################  actual script

# we want all the csv files in dbg/results/RUN_NAME/MACHINE_NAME
# the script gathers together in one file all the metrics found in dbg/results/RUN_NAME

machine_names = ['akan', 'hudson', 'ganges', 'niagara',
                 'parana', 'rhine', 'yangtze']
machine_names = [mname + '.mdg.lab' for mname in machine_names] # add .mdg.lab at the end

proxy_filename_prefix = 'proxy_resmon'
rcat_filename_prefix = 'rcat_resmon'
bot_filename_prefix = 'bot'


srvdata = [] # contains tuples of (timestamp, filename, useful_data_dict)
alldata = [{'botRtts': [],
            'sumProxiesCpuPercents': [],
            'sumRcatsCpuPercents': []
            }
           for _ in range(10 ** 4)] # list indexed by number of connected users, each cell stores a list of rtts
# we wont have more than 10k bots 
time_zero = 0 # timestamp when the last app server or proxy launched
ref_filename = '' # filename of the latest app/proxy launched


# proxy columns:
# humanTime,timestamp,numUsers,userCpuRatio,systemCpuRatio,maxResidentSetPerSec,
# pageFaultsWithoutIOPerSec,pageFaultsWithIOPerSec,blockInputOpsPerSec,
# blockOutputOpsPerSec,vContextSwitchesPerSec,ivContextSwitchesPerSec
def process_proxy_row(row, filename):
    """ """
    timestamp = float(row['timestamp'])
    cpu_percent = (float(row['userCpuRatio']) + float(row['systemCpuRatio'])) * 100
    useful_data = {'cpuPercent': cpu_percent,
                   'numUsers': int(row['numUsers']),
                   }
    tup = (timestamp, filename, useful_data)
    srvdata.append(tup)

def process_proxy_file(reader, filename):
    """ Store all the rows into the giant list.
    Update time_zero if the first timestamp is greater than the current time_zero.
    reader is a CSV DictReader
    """
    global time_zero, ref_filename
    row = reader.next()
    timestamp = float(row['timestamp'])
    if timestamp > time_zero:
        time_zero = timestamp
        ref_filename = filename
    process_proxy_row(row, filename)
    for row in reader:
        process_proxy_row(row, filename)


# app columns:
# humanTime,timestamp,userCpuRatio,systemCpuRatio,maxResidentSetPerSec,
# pageFaultsWithoutIOPerSec,pageFaultsWithIOPerSec,blockInputOpsPerSec,
# blockOutputOpsPerSec,vContextSwitchesPerSec,ivContextSwitchesPerSec

def process_rcat_row(row, filename):
    """ """
    timestamp = float(row['timestamp'])
    cpu_percent = (float(row['userCpuRatio']) + float(row['systemCpuRatio'])) * 100
    useful_data = {'cpuPercent': cpu_percent,
                   }
    tup = (timestamp, filename, useful_data)
    srvdata.append(tup)

def process_rcat_file(reader, filename):
    """ Store all the rows into the giant list.
    Update time_zero if the first timestamp is greater than the current time_zero.
    reader is a CSV DictReader
    """
    global time_zero, ref_filename
    row = reader.next()
    timestamp = float(row['timestamp'])
    if timestamp > time_zero:
        time_zero = timestamp
        ref_filename = filename
    process_rcat_row(row, filename)
    for row in reader:
        process_rcat_row(row, filename)


# bot columns:
# botname, timestamp, numUsers, rtt

def process_bot_file(reader, filename):
    """ """
    for row in reader:
        #timestamp = float(row['timestamp'])
        rtt = float(row['rtt'])
        num_users = int(row['numUsers'])
        alldata[num_users]['botRtts'].append(rtt)


# add data from all the files to the giant list
proxies_last_data = {} # keep track of the latest data struct; indexed by proxy filename
rcats_last_data = {} # indexed by rcat filename
bots_filenames = set()
bots_last_rtts = [] # all bots are grouped together during a given bucket 
for root, dirs, filenames in os.walk(run_folder):
    for filename in filenames:
        if filename.endswith('.csv'):
            print 'processing %s' % filename
            with open(os.path.join(root, filename), 'rb') as file:
                reader = csv.DictReader(file)
                if filename.startswith(proxy_filename_prefix):
                    proxies_last_data[filename] = None
                    process_proxy_file(reader, filename)
                elif filename.startswith(rcat_filename_prefix):
                    rcats_last_data[filename] = None
                    process_rcat_file(reader, filename)
                elif filename.startswith(bot_filename_prefix):
                    bots_filenames.add(filename)
                    process_bot_file(reader, filename)

# sort all proxy and rcat measurements by timestamp
srvdata.sort(key=lambda tup: tup[0])

# aggregate proxy and rcat data by buckets of timestamps.
# These buckets are the duration between 2 timestamps of the latest-launched proxy/app.
aggregates = []

for entry in srvdata:
    timestamp = entry[0]
    filename = entry[1]

    if filename in proxies_last_data: # this is a proxy data entry
        cur_data = entry[2]
        cur_data.update({'timestamp': timestamp})
        proxies_last_data[filename] = cur_data
    elif filename in rcats_last_data: # rcat entry
        cur_data = entry[2]
        cur_data.update({'timestamp': timestamp})
        rcats_last_data[filename] = cur_data

    if filename == ref_filename: # make a new bucket
        # process proxies data
        sum_proxies_cpu = 0
        sum_users = 0
        sum_rcats_cpu = 0
        # get total number of connected users by summing over all proxies
        for pdata in proxies_last_data.values():
            sum_proxies_cpu += pdata['cpuPercent']
            sum_users += pdata['numUsers']
        alldata[sum_users]['sumProxiesCpuPercents'].append(sum_proxies_cpu)
        for rdata in rcats_last_data.values():
            sum_rcats_cpu += rdata['cpuPercent']
        alldata[sum_users]['sumRcatsCpuPercents'].append(sum_rcats_cpu)




# write all aggregates
result_filename = run_folder + '/aggregates-' + run_name + '.csv'
result_file = open(result_filename, 'w', 0)
writer = csv.writer(result_file)
header = ['runName', 'numUsers',
          'totalProxyCpuPercentAvg',
          'totalProxyCpuPercentStdev',
          'totalProxyCpuPercent99',
          'proxyCpuSampleSize',
          'totalRcatCpuPercentAvg',
          'totalRcatCpuPercentStdev',
          'totalRcatCpuPercent99',
          'rcatCpuSampleSize',
          'rttAvg',
          'rttStdev',
          'rtt99',
          'rttSampleSize'
          ]
writer.writerow(header)
for num_users, data in enumerate(alldata):
    # compute proxy CPU and bot RTTs mean, stdev, and 99th percentile
    pcpus = data['sumProxiesCpuPercents']
    rcpus = data['sumRcatsCpuPercents']
    rtts = data['botRtts']
    if pcpus and rtts: # only write a row if we have data for it
        pcpu_mean, pcpu_stdev, pcpu_99 = get_stats(pcpus)
        rcpu_mean, rcpu_stdev, rcpu_99 = get_stats(rcpus)
        rtt_mean, rtt_stdev, rtt_99 = get_stats(rtts)
        row = [run_name, num_users,
               pcpu_mean, pcpu_stdev, pcpu_99, len(pcpus),
               rcpu_mean, rcpu_stdev, rcpu_99, len(rcpus),
               rtt_mean, rtt_stdev, rtt_99, len(rtts)
               ]
        writer.writerow(row)
result_file.close()

