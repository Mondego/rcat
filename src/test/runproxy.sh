#!/bin/bash
export PYTHONPATH=$PYTHONPATH:../
if [ $1 != 0 ]; then
	python ../proxy/proxymain.py --port=$1
else
	python ../proxy/proxymain.py
fi
