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

    def start(self, *args):
        """
        Start up a new process and run the main() method in the new process

        Returns:
            process id of the new process

        """
