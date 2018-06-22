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

'''Hydra is a framework (actually, currently more of a collection of classes)
that provides the basic building blocks to implement data processing software as
a graph of nodes while making heavy use of the publisher/subscriber design 
pattern.

There are four kinds of nodes in each graph:
- Sources: Nodes which are only publishing data items to subscribing nodes in 
  the graph (e.g. file readers, sockets to read data from, REST endpoints etc).
- Sinks: Nodes that are only consuming data from publishing nodes. These are the
  end-points of the graph (e.g. loggers, display widgets, sockets used to send
  data, REST endpoints etc).
- SourceSinks: Nodes that are both consuming and producing data and are graph
  end-points at the same time (e.g. sockets used to send and receive data).
- Intermediate nodes: Nodes which are both consuming (subscribers) and 
  publishing data at the same time. Such nodes can be used for various purposes
  such as buffering, examining, transforming, filtering data etc.

**WARNING**: Care must be taken when connecting multiple publishers to the same
             subscriber since in this case the subscribing node must implement a
             thread safe notify() method. If this is the case it must be noted 
             in the subscriber's doc comments, otherwise it is assumed that the
             notify() method is not thread safe and the node should not be 
             connected to more than one publisher. In this case one can use 
             a hydra_common.ActiveQueueNode, which is an essence a node that
             contains a thread-safe queue, as a man-in-the-middle to synchronize
             the access to the subscriber.
'''


import threading
import time
import logging


hydra_logger = logging.getLogger('hydra')


class Subscriber:
    '''Subscriber base class.

    Publishers that the subscruber has subscribed to, call its notify() method to
    pass data to it.

    Arguments:
      publisher: The publisher that called notify
      item: The data
    '''

    def notify(self, publisher, item):
        raise NotImplementedError('Not implemented yet')


class Publisher:
    '''Publisher base class.

    Subscribers call the subscibe method to register themselves with the publisher.
    After that, when the publisher has data, it notifies the subscriber's by
    calling their notify() method.
    '''

    def __init__(self):
        self.subscribers = set()

    def add_subscriber(self, subscriber):
        self.subscribers.add(subscriber)

    def notify_all(self, item):
        for subscriber in self.subscribers:
            subscriber.notify(self, item)


class Node:
    '''Represents a node in the processing graph.
    '''

    def __init__(self, name):
        '''Initializes the node.

        The name should be unique in the graph.
        '''
        self.name = name


class HydraError(Exception):
    """Base class for Hydra exceptions."""
    pass


class DuplicateNodeNameError(HydraError):
    """Exception raised when attempting to insert a node when a node with the
    same name already exists in the graph.

    Attributes:
        node -- the node that triggered the exception
        graph -- the graph for which the exception was triggered
    """

    def __init__(self, node, graph):
        self.node = node
        self.graph = graph

    def __str__(self):
      return "A node with the name '%s' already exists in graph '%s'" % (self.node.name, self.graph.name)


class Graph:
    ''' Represents an executable graph of nodes.

    Each node should have a unique name.
    '''

    def __init__(self, name):
        self.name = name
        self.nodes = set()
        self.executable_nodes = []

    def has_node_with_name(self, node_name):
        for n in self.nodes:
            if n.name == node_name:
                return True
        return False

    def add(self, node):
        if not self.has_node_with_name(node.name):
            self.nodes.add(node)
            if isinstance(node, threading.Thread):
                self.executable_nodes.append(node)
        else:
          raise DuplicateNodeNameError(node, self)

    def remove(self, node):
        if node in self.nodes:
            if node is threading.Thread():
                self.executable_nodes.remove(node)
            self.nodes.remove(node)

    def clear(self):
        self.nodes.clear()
        self.executable_nodes.clear()

    def execute(self):
        '''Runs the graph.
        '''
        
        # TODO: Consider scanning the graph for edge directions and start consuming
        #       nodes before producing ones.
        
        # TODO: Validate the graph prior to execution - e.g. generate warnings
        #       if cycles are detected.

        for node in self.executable_nodes:
            hydra_logger.debug('Graph %s: Starting node %s.' % (self.name, node.name))
            node.start()

    def stop(self):
        nodes = reversed(self.executable_nodes)
        for node in nodes:
            hydra_logger.debug('Graph %s: Stopping node %s...' % (self.name, node.name))
            node.stop()
        for node in nodes:
            node.join()
            hydra_logger.debug('Graph %s: Node %s has stopped.' % (self.name, node.name))


class IntermediateNode(Node, Publisher, Subscriber):
    ''' Represents a node that accepts inputs and produces outputs.

    The node follows the publisher / subscriber model to pass data around.
    When its notify() method is called for an item, it passes the item to all
    subscribers by calling its notify_all() method.
    Subclasses should override the notify() method if this behaviour is not 
    desirable.
    '''

    def __init__(self, name):
        ''' Initializes the node.
        '''
        Node.__init__(self, name)
        Publisher.__init__(self)
        Subscriber.__init__(self)

    def notify(self, publisher, item):
        '''Processes an incoming item.
        When called, passes the given item to all subscribers by calling the
        notify_all() method.
        Subclasses should override this method if this behaviour is not 
        desirable.
        '''
        self.notify_all(item)


class Stoppable():
    '''An entity that has a stop flag.
    '''

    def __init__(self):
        self.stopped = threading.Event()

    def stop(self):
        self.stopped.set()


class Source(Node, Publisher, threading.Thread, Stoppable):
    '''Represents a node that is a source of data in the graph.

    The node is only publishing data and has its own thread within which the 
    notification of subscribers should take place.
    '''

    def __init__(self, name):
        threading.Thread.__init__(self, name=name)
        Node.__init__(self, name)
        Publisher.__init__(self)
        Stoppable.__init__(self)

    def initialize(self):
        '''Initializes the source.

        Subclasses should implement this method to perform source initialization in
        the context of the source's own thread.
        '''
        pass

    def get_next_item(self):
        '''Reads the next available item.

        Returns True under normal conditions, False if the internal thread should 
        terminate (e.g. if the source is no longer in a valid state).

        Subclasses should implement this method and call notify_all(data) in it.
        '''
        time.sleep(1.0)
        return True

    def run(self):
        self.initialize()
        while not self.stopped.is_set():
            if not self.get_next_item():
                break


class Sink(Node, Subscriber):
    '''Base class for endpoint of flows in the graph.

    Subclasses should override the notify() method to actually implement the 
    processing of items. If the processing is demanding, the sink should be
    prepended with and ActiveQueueNode (this way, the processing will take place
    in the ActiveQueueNode's thread allowing the publishers to proceed with 
    notifying other subscribers).
    '''

    def __init__(self, name):
        Node.__init__(self, name)


class SourceSink(Source, Subscriber):
    '''Represents a node that is a source of data in the graph.

    The node is only publishing data and has its own thread within which the 
    notification of subscribers should take place.
    '''

    def __init__(self, name):
        Source.__init__(self, name)
        Subscriber.__init__(self)


class Filter(IntermediateNode):
    '''Base class for filter nodes.
    '''

    def __init__(self, name):
        IntermediateNode.__init__(self, name)

    def check(self, item):
        '''Checks if the given item should pass the filter.

        Subclasses should override this method to perform the actual check of the 
        filter.
        '''
        return True

    def notify(self, publisher, item):
        if self.check(item):
            self.notify_all(item)


class Transformation(IntermediateNode):
    '''Base class for nodes that "transform" their input in some way.
    '''

    def __init__(self, name):
        IntermediateNode.__init__(self, name)

    def transform(self, item):
        '''Transforms the given item.

        Subclasses should override this method.
        '''
        return item

    def notify(self, publisher, item):
        transformed_item = self.transform(item)
        if not transformed_item is None:
            self.notify_all(transformed_item)

