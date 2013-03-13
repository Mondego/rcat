#!/bin/bash
# 1: Database, 2: User, 3: password, 4: SQL script, 5: output

./util/mysql_script_executer.sh $1 rcat isnotamused ./util/mondego_mysql_clean.sql /tmp/out
