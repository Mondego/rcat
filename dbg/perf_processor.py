import csv
import os

###################  tools

# from http://stackoverflow.com/a/7464107/856897
def percentile(N, P):
    """
    Find the percentile of a list of values

    @parameter N - A list of values.  N must be sorted.
    @parameter P - A float value from 0.0 to 1.0

    @return - The percentile of the values.
    """
    n = int(round(P * len(N) + 0.5))
    return N[n - 1]



#####################  actual script

# we want all the csv files in dbg/results/RUN_NAME/MACHINE_NAME
# the script gathers together in one file all the metrics found in dbg/results/RUN_NAME

machine_names = ['akan', 'hudson', 'ganges', 'niagara',
                 'parana', 'rhine', 'yangtze']
machine_names = [mname + '.mdg.lab' for mname in machine_names] # add .mdg.lab at the end

proxy_filename_prefix = 'proxy_resmon'
rcat_filename_prefix = 'rcat_resmon'
bot_filename_prefix = 'bot'


alldata = [] # contains tuples of (timestamp, filename, useful_data_dict)
time_zero = 0 # timestamp when the last app server or proxy launched
ref_filename = '' # filename of the latest app/proxy launched


# proxy columns:
# humanTime,timestamp,numUsers,user cpu ratio,system cpu ratio,
# max resident set per sec,
# page faults w/o IO per sec,page faults with IO per sec,
# swap outs per sec,block input ops per sec,block output ops per sec,
# v context switches per sec,iv context switches per sec

def process_proxy_row(row, filename):
    """ """
    timestamp = float(row['timestamp'])
    cpu_percent = (float(row['user cpu ratio']) + float(row['system cpu ratio'])) * 100
    useful_data = {'cpuPercent': cpu_percent,
                   'numUsers': int(row['numUsers']),
                   }
    tup = (timestamp, filename, useful_data)
    alldata.append(tup)

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
# humanTime,timestamp,userTime,systemTime,max resident set,page faults w/o IO,page faults with IO,swap outs,block input ops,block output ops,v context switches,iv context switches

def process_rcat_file(reader, filename):
    pass

# bot columns:
# botname, timestamp, rtt

def process_bot_file(reader, filename):
    pass


# add data from all the files to the giant list
proxies_last_data = {} # keep track of the latest data struct
rcats_last_data = {}
for root, dirs, filenames in os.walk('results/run2'):
    for filename in filenames:
        if filename.endswith('.csv'):
            with open(os.path.join(root, filename), 'rb') as file:
                reader = csv.DictReader(file)
                if filename.startswith(proxy_filename_prefix):
                    proxies_last_data[filename] = None
                    process_proxy_file(reader, filename)
                elif filename.startswith(rcat_filename_prefix):
                    rcats_last_data[filename] = None
                    process_rcat_file(reader, filename)
                elif filename.startswith(bot_filename_prefix):
                    process_bot_file(reader, filename)

# sort the list by timestamp
alldata.sort(key=lambda tup: tup[0])

# aggregate by buckets of timestamps.
# These buckets are the duration between 2 timestamps of the latest-launched proxy/app.
aggregates = []

for entry in alldata:
    timestamp = entry[0]
    filename = entry[1]
    if filename in proxies_last_data: # this is a proxy data entry
        cur_data = entry[2]
        cur_data.update({'timestamp': timestamp})
        proxies_last_data[filename] = cur_data

    if filename == ref_filename: # make a new bucket
        sum_proxies_cpu = 0
        sum_users = 0
        for pdata in proxies_last_data.values():
            sum_proxies_cpu += pdata['cpuPercent']
            sum_users += pdata['numUsers']
        bucket = {'timestamp': timestamp,
                  'sumProxiesCpu': sum_proxies_cpu,
                  'sumUsers': sum_users}
        aggregates.append(bucket)

print alldata
print aggregates



# write all aggregates
result_filename = 'aggregates.csv'
result_file = open(result_filename, 'w', 0)
writer = csv.writer(result_file)
header = ['timestamp', 'sumUsers', 'sumProxiesCpu']
writer.writerow(header)
for agg in aggregates:
    row = [agg['timestamp'], agg['sumUsers'], agg['sumProxiesCpu']]
    writer.writerow(row)
result_file.close()

