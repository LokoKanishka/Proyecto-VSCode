import queue
import threading
import time

class BackpressureQueue:
    def __init__(self, max_size=10):
        self.queue = queue.Queue(maxsize=max_size)
        self.running = True
        
    def put_action(self, action_item, timeout=1.0):
        """
        Add an action to the queue. 
        Returns True if added, False if queue full (backpressure).
        """
        try:
            self.queue.put(action_item, timeout=timeout)
            return True
        except queue.Full:
            print("Queue full! Dropping action due to backpressure.")
            return False
            
    def process_queue(self, worker_func):
        """
        Process items using the worker_func.
        """
        while self.running:
            try:
                item = self.queue.get(timeout=1.0)
                worker_func(item)
                self.queue.task_done()
            except queue.Empty:
                continue
                
    def stop(self):
        self.running = False
