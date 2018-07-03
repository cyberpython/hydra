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


'''REST-related nodes for Hydra.
'''

from flask import Flask, request
from hydra_core import Source
from queue import Queue, Empty
# from multiprocessing import Process, Queue
from threading import Thread

class RestService(Source):
  '''Runs a Flask web-server in a separate process.
  The server accepts POST requests at the '/' endpoint in JSON encoding.
  The JSON encoding must contain a field named "data" which in turn contains
  a string of byte values encoded with 2 hex digits each. Spaces are allowed
  between the byte values.

  Subclasses can override the initialize() and process_input() methods to
  implement any REST service and endpoint.
  '''
  
  def __init__(self, name, host='0.0.0.0', port=8080):
    Source.__init__(self, name)
    self.app=Flask(self.name)
    self.host = host
    self.port = port
    self.q = Queue()
    self.server_thread = None
  
  # def process_input(self):
  #   try:
  #     data = bytes(bytearray.fromhex(request.json['data'].replace(' ', '')))
  #     self.q.put(data)
  #     return '', 200
  #   except:
  #     return 'Invalid input', 400
  
  def initialize(self):
    # self.app.add_url_rule("/", "index", self.process_input, methods=['POST'])
    
    args = {'host': self.host, 'port': self.port}
    # self.server = Process(target=self.app.run, kwargs=args)
    # self.server.start()
    self.server = Thread(target=self.app.run, kwargs=args, daemon=True)
    self.server.start()

  def stop(self):
    # self.server.terminate()
    super(RestService, self).stop()
    # self.server.join()
    
  def get_next_item(self):
    try:
      item = self.q.get(timeout=1.0)
      self.notify_all(item)
    except Empty:
      pass
    return True
  
