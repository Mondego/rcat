'''
Created on Oct 31, 2011

@author: Arthur Valadares

Proxy starts ProxyFront and ProxyBack
'''
import logging
from front import Front

if __name__ == "__main__":
    lformat = '%(asctime)s | %(levelname)s [%(name)s]: %(message)s'
    logging.basicConfig(filename='proxy.log', level=logging.INFO, format=lformat)
    logging.info("Start ProxyFront")
    x = Front.Main()
    logging.info("Start ProxyBack")
    logging.info("Proxy Started")
    