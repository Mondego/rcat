#!/bin/bash
export PYTHONPATH=$PYTHONPATH:../src

python ../src/examples/jigsaw/bot/jigsawbot.py $1 $2
