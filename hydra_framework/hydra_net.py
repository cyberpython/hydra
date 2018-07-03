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

'''Network-related nodes for Hydra.
'''

import socket
from hydra_core import SourceSink, hydra_logger


class BaseTcpHeader:
    '''Base class for TCP header helper.

    This class provides the mechanism to break the TCP stream into distinct
    messages if the messages have a fixed-size header.

    Subclasses should override the get_message_size() method.
    '''

    def __init__(self, header_length):
        self.header_length = header_length

    def get_message_size(self, header_bytes):
        '''Returns the number of bytes that need to be read from the TCP stream 
        (excluding the header bytes) to read a complete message. If the messages are
        fixed-size, then this method should always return the same value, whereas if
        the message size is defined as part of the header it should extract it and
        return it.

        Arguments:
          - header_bytes: The bytes of the header.
        '''
        raise NotImplementedError('Not implemented yet')


class TcpSourceSink(SourceSink):
    '''Represents source/sink nodes that are backed by a TCP socket.

    The TCP server only accepts one client at a time.

    **WARNING**: Please note that reconnections have not been implemented,
                 i.e. if the remote endpoint diconnects, the node terminates
                 its execution. For TCP servers, this means that if a client
                 connects, then after it has disconnected the server does not
                 accept any new connections.
    '''

    def __init__(self, name, ip_address, port, tcp_header,
                 is_server=False, keep_header_data=True):
        SourceSink.__init__(self, name)
        self.ip_address = ip_address
        self.port = port
        self.is_server = is_server
        self.keep_header_data = keep_header_data
        self.server_sock = None
        self.sock = None
        self.sock_timeout = 1.0
        if tcp_header is None:
            raise ValueError('tcp_header cannot be None')
        else:
            self.tcp_header = tcp_header

    def initialize(self):
        if self.is_server:
            self.server_sock = socket.socket(socket.AF_INET,
                                             socket.SOCK_STREAM)
            self.server_sock.settimeout(self.sock_timeout)
            self.server_sock.bind((self.ip_address, self.port))
            self.server_sock.listen(1)
            while not self.stopped.is_set():
                try:
                    self.sock, addr = self.server_sock.accept()
                    hydra_logger.info(
                        '%s: New TCP connection from: %s' % (self.name, addr))
                    break
                except socket.timeout:
                    pass
                except OSError:
                    pass
        else:
            self.sock = socket.socket(socket.AF_INET,
                                      socket.SOCK_STREAM)
            self.sock.settimeout(self.sock_timeout)
            while not self.stopped.is_set():
                try:
                    self.sock.connect((self.ip_address, self.port))
                    hydra_logger.info(
                        '%s: Established TCP connection to: %s:%d' % (self.name, self.ip_address, self.port))
                    break
                except socket.timeout:
                    pass
                except OSError:
                    pass

    def get_next_item(self):
        try:
            self.sock.settimeout(self.sock_timeout)  # restore the timeout
            header_bytes = b''
            if self.tcp_header.header_length > 0:
                header_bytes = self.sock.recv(self.tcp_header.header_length)
                if not header_bytes:
                    self.sock.close()
                    self.sock = None
                    return False
            bytes_to_read = self.tcp_header.get_message_size(header_bytes)
            bytes_read = 0
            data = b''

            # Do not timeout between header and data
            self.sock.settimeout(None)

            while (bytes_read < bytes_to_read) and (not self.stopped.is_set()):
                tmp_data = self.sock.recv(bytes_to_read - bytes_read)
                if not tmp_data:
                    self.sock.close()
                    self.sock = None
                    return False
                else:
                    bytes_read += len(tmp_data)
                    data += tmp_data
            if bytes_read == bytes_to_read:
                if self.tcp_header.header_length > 0:
                    if self.keep_header_data:
                        data = header_bytes + data
                hydra_logger.debug('Receive %s: %d bytes' %
                                    (self.name, len(data)))
                self.notify_all(data)
            self.sock.settimeout(self.sock_timeout)  # restore the timeout
            return True
        except socket.timeout:
            return True
        except ConnectionError:
            self.sock.close()
            self.sock = None
            return False
    
    def run(self):
        self.initialize()
        while not self.stopped.is_set():
            if not self.get_next_item():
                if not self.is_server:
                    self.initialize()
                else:
                    while not self.stopped.is_set():
                        try:
                            self.sock, addr = self.server_sock.accept()
                            hydra_logger.info(
                                '%s: New TCP connection from: %s' % (self.name, addr))
                            break
                        except socket.timeout:
                            pass

    def notify(self, publisher, item):
        if not self.sock is None:
            hydra_logger.debug('Send %s: %d bytes' % (self.name, len(item)))
            self.sock.send(item)


class UdpSourceSink(SourceSink):
    '''Represents source/sink nodes that are backed by a UDP socket.
    '''

    def __init__(self, name, buffer_size, listen_ip_address=None,
                 listening_port=5632, send_to_ip=None, send_to_port=5632):
        SourceSink.__init__(self, name)
        self.buffer_size = buffer_size
        self.listen_ip_address = listen_ip_address
        self.listening_port = listening_port
        self.send_to_ip = send_to_ip
        self.send_to_port = send_to_port
        # TODO: Add multicast socket support

    def initialize(self):
        self.sock = socket.socket(socket.AF_INET,  # Internet
                                  socket.SOCK_DGRAM)  # UDP
        self.sock.settimeout(1.0)
        if not self.listen_ip_address is None:
            self.sock.bind((self.listen_ip_address, self.listening_port))

    def get_next_item(self):
        try:
            data = self.sock.recv(self.buffer_size)
            if not data:
                self.sock.close()
                self.sock = None
                return False
            else:
                hydra_logger.debug('Receive %s: %d bytes' %
                                    (self.name, len(data)))
                self.notify_all(data)
                return True
        except socket.timeout:
            return True

    def notify(self, publisher, item):
        if not self.send_to_ip is None:
            if not self.sock is None:
                hydra_logger.debug('Send %s: %d bytes' %
                                    (self.name, len(item)))
                self.sock.sendto(item, (self.send_to_ip, self.send_to_port))
