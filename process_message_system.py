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
    def main():
        """Set up the communication mechanism"""

    def start():
        """
        Start up a new process and run the main() method in the new process

        Returns:
            process id of the new process

        """
