#!/bin/bash

cat ~/.ssh/id_rsa.pub | ssh $1@$2 'cat >> .ssh/authorized_keys'
#echo "$1 ALL=(ALL) NOPASSWD: ALL" | ssh $1@$2 'bash sudo cat >> /etc/sudoers'
