#!/bin/bash
export PYTHONPATH=$PYTHONPATH:../src
if [ "$1" != "" ]; then
	python ../src/proxy/proxymain.py --port=$1
else
	python ../src/proxy/proxymain.py
fi
