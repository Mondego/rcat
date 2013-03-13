#!/usr/bin/python
import os
import sys
import subprocess as sub

f = open("mondego_servers")

def help_msg():
	print help_message
	exit()

help_message = "Use: 'ssh','update','cleanup','stop,','status','collect {run_name}'"
list_servers = f.read().splitlines()
f.close()
os.system("echo ");
for line in list_servers:
	if line and not line.startswith('#'):
		user,host = line.split(' ')
		add = user + "@" + host
		if (len(sys.argv) > 1):
			if( sys.argv[1] == 'ssh' ):
				os.system("bash authorize_ssh.sh " + line)
			elif( sys.argv[1] == 'update'):
				os.system("ssh " + add + " \' sudo apt-get update\'")
				os.system("ssh " + add + " \' sudo apt-get -y upgrade\'")
			elif( sys.argv[1] == 'cleanup'):
				os.system("ssh " + add +" \' rm -rf ~/rcat\'")
			elif( sys.argv[1] == 'stop'):
				os.system("ssh " + add + " \' killall screen\'")
			elif( sys.argv[1] == 'status'):
				os.system("ssh " + add + " \' screen -list\'")
			elif( sys.argv[1] == 'collect'):
				if len(sys.argv) == 3:
					run_name = sys.argv[2]
					results_folder = "../../results/%s/%s" % (run_name,host)
					if os.path.exists(results_folder):
						print "This run name already exists. Delete the run_name or use a different one"
						sys.exit(0)
					# Create the runname folder
					os.system('mkdir -p ' + results_folder) 
					# Find all csv files in the remove machine
					args = "ssh",add,"find ~/rcat | grep .csv"
					p = sub.Popen(args,stdout=sub.PIPE,stderr=sub.PIPE)
					output, errors = p.communicate()

					csvs = output.splitlines()
					# For every csv file, copy it to the results folder
					for f in csvs:
						os.system('scp %s:%s %s' % (add,f,results_folder))
				else:
					print "./mondego_utils collect {run_name}"

				
			else:
				help_msg()
		else:
			help_msg()

