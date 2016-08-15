import atexit
import os
import pickle
import queue
import sys
import tempfile
import threading
import time

ANY = 'any'

class Message():
    def __init__(self, label, guard = lambda: True, action = lambda: None):
        self.label = label
        self.guard = guard
        self.action = action

class TimeOut():
    def __init__(self, time, action):
        self.time = time
        self.action = action

class MessageProc():
    pipe_path_prefix = tempfile.gettempdir() + '/pipe'

    def __init__(self):
        self.arrived_condition = threading.Condition()
        self.pipe_path = self.pipe_path_prefix + str(os.getpid())
        self.pipes_written = {}
        self.queue = queue.Queue()
        self.message_list = []

    def main(self):
        """Set up the communication mechanism"""
        if not os.path.exists(self.pipe_path):
            os.mkfifo(self.pipe_path)
        atexit.register(self.clean_up)
        threading.Thread(target = self.read_pipe, daemon = True).start()

    def start(self, *args):
        """
        Start up a new process and run the main() method in the new process

        Returns:
            process id of the new process

        """

    def read_pipe(self):
        """Continuously load data from pipe into synchronized queue"""
        with open(self.pipe_path, 'rb') as pipe:
            while True:
                try:
                    self.queue.put(pickle.load(pipe))
                    self.arrived_condition.notify()
                except EOFError:
                    time.sleep(1)

    def clean_up(self):
        """Close all the pipes to which this process has written and remove the pipe of itself"""
        for pid, pipe in self.pipes_written:
            pipe.close();
        os.remove(self.pipe_path)
