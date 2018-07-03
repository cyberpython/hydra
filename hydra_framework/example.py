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

'''Example program for Hydra.
This program creates a graph that contains a TCP server source, a queue and a 
UDP sink. The goal is to receive a message from TCP and send it over UDP. It
also contains a logging node that logs all the incoming message data.
'''

from hydra_core import Graph
from hydra_common import ActiveQueueNode, LoggerNode
from hydra_net import UdpSourceSink, TcpSourceSink, BaseTcpHeader
from hydra_rest import RestService
import time
import logging
import struct

class MyTcpHeader(BaseTcpHeader):
  '''Sample TCP header representation class for TCP messages with the following
  header structure (big endian):
  - sequence number (16-bits unsigned)
  - length (8-bits unsigned)
  '''

  def __init__(self):
    BaseTcpHeader.__init__(self, 3)
  
  def get_message_size(self, header_bytes):
    '''Here we use Python's built-in `struct` module to convert the raw bytes to
    values but if we needed more control (e.g. on the bit-level) other means 
    could be used (e.g. the bitstring module available on pip)
    '''
    seq_no, length = struct.unpack('>HB', header_bytes) # extract an unsigned short and an unsigned byte(the '>' means big endian)
                                                        # for details see: https://docs.python.org/3.5/library/struct.html
    return length


# if this script is being executed as a program:
if __name__ == '__main__':
  
  # setup logging:
  logging.basicConfig(level=logging.INFO)

  # create a graph:
  g = Graph('G1')

  # Create a UDP source:
  # src1 = UdpSourceSink('UDP Source #1', 1024, listen_ip_address='0.0.0.0', listening_port=1998)
  # Create a TCP server source:
  header = MyTcpHeader()
  src1 = TcpSourceSink('TCP Source #1', ip_address='0.0.0.0', port=1998, tcp_header=header, is_server=True, keep_header_data=True)
  
  # Create a queue and connect it to the source:
  queue1 = ActiveQueueNode('Queue #1')
  src1.add_subscriber(queue1)

  src2 = RestService('REST source #1', host='0.0.0.0', port=5002)
  src2.add_subscriber(queue1)

  # Create a UDP sink that sends to 127.0.0.1:6544 and connect it to the queue:
  sink1 = UdpSourceSink('UDP Sink #1', 1024, send_to_ip='127.0.0.1', send_to_port=6544)
  queue1.add_subscriber(sink1)

  # Create a logging node and connect it the source as well
  log1 = LoggerNode('Logging #1', logging.INFO)
  src1.add_subscriber(log1)
  
  # Add all the nodes to the graph:
  g.add(src1)
  g.add(src2)
  g.add(queue1)
  g.add(sink1)
  g.add(log1)

  # Execute the graph:
  g.execute()
  
  # Wait for CTRL-C and then stop the graph execution:
  while True:
    try:
      time.sleep(1)
    except KeyboardInterrupt:
      g.stop()
      break
