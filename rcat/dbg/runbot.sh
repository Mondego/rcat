#!/bin/bash

# $1 is ip
# $2 is port
# $3 is number of bots

EXPECTED_ARGS=3
E_BADARGS=65

if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` {ip} {port} {number of bots}"
	exit $E_BADARGS
else
	echo "Launching $3 bots to $1:$2"
fi

export PYTHONPATH=$PYTHONPATH:../src
for i in $(eval echo {1..$3})
do
	screen -d -m python ../src/examples/jigsaw/bot/jigsawbot.py -ip $1 -p $2
   #python ../src/examples/jigsaw/bot/jigsawbot.py -ip $1 -p $2
   sleep .5
done
