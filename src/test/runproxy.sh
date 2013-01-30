#!/bin/bash
export PYTHONPATH=$PYTHONPATH:../
if [ "$1" != "" ]; then
	python ../proxy/proxymain.py --port=$1 --benchmark
else
	python ../proxy/proxymain.py --benchmark
fi
