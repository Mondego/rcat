#!/bin/bash

# $1 is ip
# $2 is port
# $3 is number of bots

EXPECTED_ARGS=1
E_BADARGS=65

if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` {number of bots}"
	exit $E_BADARGS
else
	echo "Launching $1 bots"
fi

export PYTHONPATH=$PYTHONPATH:../src
for i in $(eval echo {1..$1})
do
	screen -d -m python dummybot.py
   #python ../src/examples/jigsaw/bot/jigsawbot.py -ip $1 -p $2
   sleep 1
done
