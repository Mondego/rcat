from time import sleep
import logging.config
import tornado.ioloop
import tornado.web
import tornado.websocket

log = logging.getLogger('dummysrv')

class WSHandler(tornado.websocket.WebSocketHandler):
    
    def open(self):
        """ send a message, wait a sec, then resend a msg """
        #log.info(str(self.request.connection.address) + ' joined')
        
        self.write_message("Hello from serv")
        #sleep(1)
        #self.write_message("Hello from serv again")
      
      
    def on_message(self, message):
        #log.debug(str(self.request.connection.address) + ' says: ' + message)
        self.write_message("Thanks for your msg: \'" + message + '\'')


    def on_close(self):
        #log.info(str(self.request.connection.address) + ' left')
        pass
      

handlers = (r'/ws', WSHandler),
app = tornado.web.Application(handlers)


if __name__ == "__main__":
    logging.config.fileConfig("logging.conf")
    
    app.listen(9000) # TODO: from config file instead 
    log.info('server listens on 9000')
    tornado.ioloop.IOLoop.instance().start()
