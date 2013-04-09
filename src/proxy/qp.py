'''
Queue processor: process queues of messages to send to clients.

'''
import threading
import time

class QueueProcessor:
    
    def __init__(self, proxyref, proxy_options):
        """ """
        self.proxyref = proxyref
        # create a recurrent timer processing the queues
        self.timer_delay = 0.01 # in seconds
        threading.Thread(target=self.process_queues).start() 
        
        
    def process_queues(self):
        """ Send all messages in each queue to each handler.
        When done, schedule another processing of the queues.
        """
        while True:
            start_time = time.time()
            for handler, q in self.proxyref.msg_queues.items():
                while q:
                    try:
                        msg = q.popleft() # q is a deque
                        handler.write_message(msg)
                    except IndexError: # cant pop empty deque 
                        pass
            process_time = time.time() - start_time
            # increase or decrease delay if late/early
            if process_time > 1.5 * self.timer_delay:
                self.timer_delay = 1.2 * self.timer_delay
            elif process_time < 0.5 * self.timer_delay:
                self.timer_delay = max(0.8 * self.timer_delay, 0.01) # sleep at least 10ms 
            time.sleep(self.timer_delay)