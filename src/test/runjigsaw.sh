#!/bin/bash
export PYTHONPATH=$PYTHONPATH:~/rcat:~/Dropbox/rcat/src
cd ~/rcat/test

python ../examples/jigsaw/server/jigsawapp.py
#python jigsawapp.py -p 20002 -ip opensim.ics.uci.edu
#python jigsawapp.py -p 20003 -ip opensim.ics.uci.edu
#python jigsawapp.py -p 20004 -ip opensim.ics.uci.edu
