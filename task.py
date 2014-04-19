# -*- coding: utf-8 -*-

# Copyright (c) 2014 Wei-Cheng Pan (潘韋成) <legnaleurc@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import threading


class EventLoop(object):

    def __init__(self):
        self._worker = _Worker()
        self._id_counter = 0
        self._timers = {}

    def start(self):
        self._worker.start()

    def stop(self):
        self._worker.stop()

    def set_timeout(self, sec, callback):
        token = self._id_counter
        self._id_counter += 1

        timer = threading.Timer(sec, lambda: self._on_timeout(token, callback))
        self._timers[token] = timer
        timer.start()

        return token

    def clear_timeout(self, token):
        if token not in self._timers:
            return

        timer = self._timers[token]
        del self._timers[token]
        timer.cancel()

    def _on_timeout(self, token, callback):
        if token not in self._timers:
            return

        timer = self._timers[token]
        del self._timers[token]
        self._worker.enqueue(callback)


class _Worker(threading.Thread):

    def __init__(self):
        super().__init__(self)

        self._should_stop = False

        self._queue = []
        self._condition = threading.Condition()
        self._queue_lock = threading.RLock()

    def run(self):
        while True:
            # sleep until task arrive
            with self._condition:
                self._condition.wait()

            # consume task queue
            while not self._should_stop:
                with self._queue_lock:
                    if len(self._queue) > 0:
                        task = self._queue.pop(0)
                    else:
                        task = None

                if not task:
                    break
                task()

            # check stop status
            if self._should_stop:
                return

    def enqueue(self, task):
        if self._should_stop:
            return

        with self._queue_lock:
            self._queue.append(task)

        # notify worker to consume
        with self._condition:
            self._condition.notifyAll()

    def stop(self):
        self._should_stop = True

        # notify worker to consume
        with self._condition:
            self._condition.notifyAll()
