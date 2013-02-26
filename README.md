A web server for massively multi-user online applications.

Requirements
---

- Tornado Web Server (http://www.tornadoweb.org/)
- Websocket client 0.8.0 (http://pypi.python.org/pypi/websocket-client/)
- Python 2.7
- Python-MySQLDB (http://sourceforge.net/projects/mysql-python/)
- Python-SQLAlchemy 0.7 (http://www.sqlalchemy.org/). You may need python-sqlalchemy and python-sqlalchemy-ext.


Requirements in Ubuntu
---

To install all required packages in ubuntu, do:
sudo apt-get install python python-tornado python-sqlalchemy 
Follow instructions for the Websocket client.


Jigsaw setup
--- 

After installing all the required libraries, follow these 3 steps to start the server

1. cd into bin directory
2. Copy rcat.cfg.example and jigsaw.cfg.example to rcat.cfg and jigsaw.cfg respectively. Configure both files with host name and mysql credentials (default: localhost)
3. run ./runproxy.sh
4. run ./runjigsaw.sh
5. By default, the client in static/jigsaw.html connects to localhost. If deploying externally, modify the server URL in jigsaw.html accordingly.

bots:

6. cd /dbg
7. ./runbot.sh ip port numbots


Now point your browser at <host>:8888/static/jigsaw.html, change the host name and click Connect!


Database checks
---

- mysql -u jigsawuser -p 
- then enter password
- use jigsawdb
- select * from jigsawpieces
