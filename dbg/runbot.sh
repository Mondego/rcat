#!/bin/bash
export PYTHONPATH=$PYTHONPATH:../src

for i in {0..$3}
do
	screen -d -m python ../src/examples/jigsaw/bot/jigsawbot.py $1 $2
done
