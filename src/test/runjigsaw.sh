#!/bin/bash
export PYTHONPATH=$PYTHONPATH:~/rcat:~/Dropbox/rcat/src
cd ~/rcat/test

python ../examples/jigsaw/server/jigsaw.py
