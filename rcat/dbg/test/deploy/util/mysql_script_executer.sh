#!/bin/bash
# 1: Database, 2: User, 3: password, 4: SQL script, 5: output


mysql $1 -u $2 --password=$3 < $4 > $5
