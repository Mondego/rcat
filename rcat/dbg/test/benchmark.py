#!/usr/bin/python

from time import time
from copy import deepcopy
first = time()
mat = []
line = [ set() for _ in range(0,100)]
for _ in range(0,100):
	mat.append(deepcopy(line))
second = time()
for a in mat:
	for b in a:
		b.add("Hi")

third = time()

print second-first
print third-second




