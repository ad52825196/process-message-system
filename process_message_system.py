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

    def init(self):
        """Initialise all instance fields"""
        self.pipe_path = self.pipe_path_prefix + str(os.getpid())
        self.message_list = []
        self.pipes_written = {}
        self.queue = queue.Queue()
        self.arrived_condition = threading.Condition()

    def main(self):
        """Set up the communication mechanism"""
        self.init()
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
            sys.exit()
        else:
            return pid

    def give(self, pid, label, *values):
        """Send a message to the process with pid. If its pipe does noe exist, wait for a while and check again. If its pipe was there but has disappeared, which means the receiver has left, do not send messages anymore and raise an exception"""
        pipe_to_write = self.pipe_path_prefix + str(pid)
        if pid in self.pipes_written:
            if not os.path.exists(pipe_to_write):
                raise IOError("Receiver has exited")
            else:
                pipe = self.pipes_written[pid]
        else:
            while not os.path.exists(pipe_to_write):
                time.sleep(1)
            pipe = open(pipe_to_write, 'wb')
            self.pipes_written[pid] = pipe
        pickle.dump((label, values), pipe)

    def check_match(message, expected_messages_dict):
        """
        Check whether the message is expected

        Returns:
            the corresponding expected message or None if the message is not expected

        """
        labels = [message[0], ANY]
        for label in labels:
            if label in expected_messages_dict:
                expected_message = expected_messages_dict[label]
                if expected_message.guard():
                    return expected_message
        return None

    def read_pipe(self):
        """Continuously load data from pipe into synchronized queue"""
        with open(self.pipe_path, 'rb') as pipe:
            while True:
                try:
                    self.queue.put(pickle.load(pipe))
                    with self.arrived_condition:
                        self.arrived_condition.notify()
                except EOFError:
                    time.sleep(1)

    def clean_up(self):
        """Close all the pipes to which this process has written and remove the pipe of itself"""
        for pid, pipe in self.pipes_written.items():
            pipe.close();
        if os.path.exists(self.pipe_path):
            os.remove(self.pipe_path)
