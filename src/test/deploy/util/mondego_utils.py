#!/usr/bin/python
import os
import sys
import subprocess

f = open("mondego_servers")

def help_msg():
	print help_message
	exit()

help_message = "Use: 'ssh','update','cleanup','stop,','status','getip'"
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
			else:
				help_msg()
		else:
			help_msg()

