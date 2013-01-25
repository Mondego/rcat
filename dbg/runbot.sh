#!/bin/bash
export PYTHONPATH=$PYTHONPATH:../src
for i in $(eval echo {1..$3})
do
	screen -d -m python ../src/examples/jigsaw/bot/jigsawbot.py -ip $1 -p $2
	sleep 2
done
