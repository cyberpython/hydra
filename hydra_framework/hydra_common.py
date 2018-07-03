#!/usr/bin/python3

# Copyright (C) 2018, Georgios Migdos <giorgos.migdos@gmail.com>
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

'''Commonly used Hydra nodes.
'''

import logging
import threading
from queue import Queue, Empty
from hydra_core import IntermediateNode, Stoppable, Sink, hydra_logger

class ActiveQueueNode(IntermediateNode, threading.Thread, Stoppable):
    '''Represents a node that stores items in a queue.

    The node is "active", in the sense that it run its own thread that retrieves
    items from the queue and passes them to subscribers.
    
    The notify() method is thread-safe.
    '''

    def __init__(self, name):
        threading.Thread.__init__(self, name=name)
        IntermediateNode.__init__(self, name)
        Stoppable.__init__(self)
        self.queue = Queue()

    def notify(self, publisher, item):
        hydra_logger.debug('Queue %s - put: %s' % (self.name, str(item)) )
        self.queue.put(item)

    def run(self):
        hydra_logger.debug('Queue %s - running.' % (self.name) )
        while not self.stopped.is_set():
            hydra_logger.debug('Queue %s - retrieving...' % (self.name) )
            try:
                item = self.queue.get(timeout=1.0)
                hydra_logger.debug('Queue %s - got: %s' % (self.name, str(item)) )
                self.notify_all(item)
            except Empty:
                pass

class LoggerNode(Sink):
  '''Node that logs each incoming item.

  Subclasses should override the to_string() method to convert items to strings.
  '''

  def __init__(self, name, level):
    Sink.__init__(self, name)
    self.logger = logging.getLogger(self.name)
    self.level = level

  def to_string(self, item):
    return str(item)

  def notify(self, publisher, item):
    self.logger.log(self.level, 'From %s: %s' % (publisher.name, self.to_string(item)))

