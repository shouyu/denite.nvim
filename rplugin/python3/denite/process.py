# ============================================================================
# FILE: process.py
# AUTHOR: Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
# ============================================================================

import subprocess
from threading import Thread
from queue import Queue
from time import time
from collections import deque


class Process(object):
    def __init__(self, commands, context, cwd):
        self.__proc = subprocess.Popen(commands,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       cwd=cwd)
        self.__eof = False
        self.__context = context
        self.__thread = Thread(target=self.enqueue_output)
        self.__thread.start()
        self.__queue_out = Queue()
        self.__outs = []

    def eof(self):
        return self.__eof

    def kill(self):
        if not self.__proc:
            return
        self.__proc.kill()
        self.__proc = None
        self.__queue_out = None
        self.__thread = None
        self.__outs = None

    def enqueue_output(self):
        for line in self.__proc.stdout:
            self.__queue_out.put(
                line.decode(self.__context['encoding'],
                            errors='replace').strip('\n'))

    def communicate(self, timeout):
        if not self.__proc:
            return ([], [])

        start = time()
        outs = deque()

        while not self.__queue_out.empty() and time() < start + timeout:
            outs.append(self.__queue_out.get_nowait())

        outs = list(outs)
        if self.__outs:
            outs = self.__outs + outs
            self.__outs = None

        if self.__thread.is_alive() or not self.__queue_out.empty():
            if len(outs) < 5000:
                # Skip the update
                self.__outs = outs
                return ([], [])
            return (outs, [])

        _, errs = self.__proc.communicate(timeout=timeout)
        errs = errs.decode(self.__context['encoding'],
                           errors='replace').split('\n')
        self.__eof = True
        self.__proc = None
        self.__thread = None
        self.__queue = None

        return (outs, errs)
