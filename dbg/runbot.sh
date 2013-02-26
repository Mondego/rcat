#!/bin/bash

# $1 is ip
# $2 is port
# $3 is number of proxies

echo "Launching $3 bots to $1:$2"

export PYTHONPATH=$PYTHONPATH:../src
for i in $(eval echo {1..$3})
do
	screen -d -m python ../src/examples/jigsaw/bot/jigsawbot.py -ip $1 -p $2
	sleep 2
done
