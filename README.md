Hydra Framework
===============


Description
-----------

Hydra is a framework (actually, currently more of a collection of classes)
that provides the basic building blocks to implement data processing software as
a graph of nodes while making heavy use of the publisher/subscriber design 
pattern.

There are four kinds of nodes in each graph:

- Sources: Nodes which are only publishing data items to subscribing nodes in 
  the graph (e.g. file readers, sockets to read data from, REST endpoints etc).

- Sinks: Nodes that are only consuming data from publishing nodes. These are the
  end-points of the graph (e.g. loggers, display widgets, sockets used to send
  data, REST endpoints, websockets etc).

- SourceSinks: Nodes that are both consuming and producing data and are graph
  end-points at the same time (e.g. sockets used to send and receive data).

- Intermediate nodes: Nodes which are both consuming (subscribers) and 
  publishing data at the same time. Such nodes can be used for various purposes
  such as buffering, examining, transforming, filtering data etc.


The available classes are broken down to the following modules:

- `hydra_core`: Contains the basic classes from which graphs are built.
- `hydra_common`: Classes for commonly used node types (e.g. queues).
- `hydra_net`: TCP and UDP SourceSinks.
- `hydra_rest`: REST API endpoint node (uses `Flask` and its built-in 
                development server).

Installation
------------

Install with `pip`:

    pip install hydra-framework

Examples
--------

See `example.py`.


TODO
----

- Implement the following modules:
  + `hydra_websocket`: Module that provides REST and websocket sinks and sources.
  + `hydra_gui_qt5`: Module that provides GUI components for QT5 (Python for QT).
- Add a REST client node implementation based on the `requests` module.


Requirements
------------

- Python 3.x
- Flask (for hydra-rest)


License
-------

MIT license
