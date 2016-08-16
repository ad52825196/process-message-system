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
            pipe = self.pipes_written[pid]
        else:
            while not os.path.exists(pipe_to_write):
                time.sleep(0.1)
            pipe = open(pipe_to_write, 'wb')
            self.pipes_written[pid] = pipe
        try:
            pickle.dump((label, values), pipe)
            pipe.flush()
        except BrokenPipeError:
            return

    def receive(self, *args):
        """
        Find the first message in the message list which matches one of the arguments and delete this message from the list. If nothing in the message list matches, blocks and imports data from the queue until there is a message coming in which is expected

        Returns:
            whatever the action function inside the matched argument returns

        """
        timeout = None
        expected_messages_list = []
        for expected_message in args:
            if isinstance(expected_message, Message):
                expected_messages_list.append(expected_message)
            elif isinstance(expected_message, TimeOut) and timeout is None:
                timeout = expected_message

        matched_expected = None
        matched_message = None
        for message in self.message_list[:]:
            matched_expected = MessageProc.check_match(message, expected_messages_list)
            if matched_expected is not None:
                matched_message = message
                self.message_list.remove(message)
                return matched_expected.action(*matched_message[1])

        queue_has_been_emptied = False
        waiting_time = None
        if timeout is not None:
            waiting_time = timeout.time
        while matched_expected is None:
            try:
                if not queue_has_been_emptied:
                    message = self.queue.get(False)
                else:
                    if waiting_time is not None and waiting_time <= 0:
                        raise queue.Empty()
                    start_time = time.time()
                    message = self.queue.get(timeout = waiting_time)
                    end_time = time.time()
                    if waiting_time is not None:
                        waiting_time -= end_time - start_time
            except queue.Empty:
                if not queue_has_been_emptied:
                    queue_has_been_emptied = True
                else:
                    return timeout.action()
            else:
                matched_expected = MessageProc.check_match(message, expected_messages_list)
                if matched_expected is None:
                    self.message_list.append(message)
                else:
                    matched_message = message
                self.queue.task_done()
        return matched_expected.action(*matched_message[1])

    def check_match(message, expected_messages_list):
        """
        Check whether the message is expected

        Returns:
            the corresponding expected message or None if the message is not expected

        """
        for expected_message in expected_messages_list:
            if (message[0] == expected_message.label or expected_message.label == ANY) and expected_message.guard():
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
                    time.sleep(0.1)

    def clean_up(self):
        """Close all the pipes to which this process has written and remove the pipe of itself"""
        for pid, pipe in self.pipes_written.items():
            pipe.close();
        if os.path.exists(self.pipe_path_prefix + str(os.getpid())):
            os.remove(self.pipe_path_prefix + str(os.getpid()))
