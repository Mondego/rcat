#!/bin/bash/

sudo apt-get -y install python python-setuptools python-mysqldb python-sqlalchemy
cd ~/rcat/test/deploy/lib

tar xvzf tornado-2.3.tar.gz
cd tornado-2.3/
sudo python setup.py install
cd ../

tar xvzf websocket-client-0.8.0.tar.gz
cd websocket-client-0.8.0
sudo python setup.py install
cd ..

sudo rm -rf tornado-2.3
sudo rm -rf websocket-client-0.8.0
