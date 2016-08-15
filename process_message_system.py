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
        pid = os.fork()
        if pid == 0:
            self.main(*args)
        else:
            return pid

    def give(self, pid, label, *values):
        """Send a message to the process with pid. If its pipe does noe exist, wait for a while and check again. If its pipe was there but has disappeared, which means the receiver has left, do not send messages anymore."""
        pipe_to_write = self.pipe_path_prefix + pid
        if pid in self.pipes_written.keys():
            if not os.path.exists(pipe_to_write):
                raise ReceiverHasExitedError
            else:
                pipe = self.pipes_written[pid]
        else:
            while not os.path.exists(pipe_to_write):
                time.sleep(1)
            pipe = open(pipe_to_write, 'wb')
            self.pipes_written[pid] = pipe
        pickle.dump((label, values), pipe)

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
