import json
import logging.config
import thread
import time
import websocket
from common.message import MESSAGE_TYPE

def on_message(ws, message):
    msg = json.loads(message)
    if "T" in msg:
        if msg["T"] == MESSAGE_TYPE.CONNECT:
            # Just accept connections as they come for now
            msg["T"] = MESSAGE_TYPE.ACCEPTED
            proxy_msg = json.dumps(msg)
        ws.send(proxy_msg)

def on_error(ws, error):
    print error

def on_close(ws):
    print "### closed ###"

def on_open(ws):
    def run(*args):
        for i in range(3):
            time.sleep(1)
            ws.send("Hello %d" % i)
        time.sleep(1)
        ws.close()
        print "thread terminating..."
    thread.start_new_thread(run, ())


if __name__ == "__main__":
    websocket.enableTrace(True)
    logging.config.fileConfig("logging.conf")
    logging.debug("[ProxyConnector]: Starting Proxy")
    ws = websocket.WebSocketApp("ws://localhost:8888/server",
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open

    ws.run_forever()