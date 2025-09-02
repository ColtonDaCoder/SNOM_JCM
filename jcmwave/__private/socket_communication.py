# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Philipp Schneider
#                 (based on daemon code by Carlo Barth, Martin Hammerschidt)
#
#SVN-File version: $Rev: 3237 $


import sys
import time
import threading 
import tempfile
import re # regular expression parsing
from subprocess import Popen
import socket # TCP communication
import struct
from jcmwave.__private import socket_lock
from jcmwave.__private.warning import warning


def send_message(socket, message, get_answer=True):
    """
    Sends message via socket
    Returns the answer sent via the socket
    """
    global socket_lock
    with socket_lock:
        socket.sendall( _CommandLength2ByteArray(message) ) # send command length
        socket.sendall( message.encode() ) # send command
    
        if get_answer:
            answer = _recv_size( socket )
        else:
            answer = None
    return answer
    


def run_command(JCMsolve, command, calling_pid, defaultPort=None):
    """
    Runs JCMsolve with a specific command in order to start a process
    Binds the calling pid to the process
    returns information on signature, port and socket
    """
    
    # Generate temporary files for errors and log
    error_file = tempfile.NamedTemporaryFile(suffix='.err.jcm', mode='w+b')
    log_file = tempfile.NamedTemporaryFile(suffix='.log.jcm',  mode='w+b')
    
    # Generate the command
    cmd = [JCMsolve, command, '--bound', str(calling_pid), 
          '--response_format', 'python']

    if defaultPort is not None:
        cmd.append('--port')
        cmd.append(str(defaultPort))
        
    # System call
    p = Popen(cmd, stdout=log_file, stderr=error_file)
    p.wait()
    log_file.seek(0)
    error_file.seek(0)
    
    # Read back stdout and stderr from the files
    log = log_file.readlines()
    errs = error_file.readlines()

    # Get the port number from the log_file
    for line in log:
        reStr = 'running on port (?P<port>\d+) '
        reStr += 'with signature (?P<signature>\w*)'
        match = re.findall(reStr, str(line))
        if not match == []:
            port, signature = match[0]
            port = int(port)
    url = 'localhost:{0}'.format(port)
        
    # Close the log and error files (deletes them automatically!)
    error_file.close()
    log_file.close()
    
    handshakeOK = True
    # Communicate with the daemon via TCP/IP
    handshake = signature
    handShakeConfirmSignal = '__JCM_HANDSHAKE_OK__'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    s.settimeout(None)
    s.sendall(handshake.encode())
    data = s.recv(4096)
    handshakeOK = (data.decode() == handShakeConfirmSignal)
    python_socket = s
    if not handshakeOK:
        raise RuntimeError(
          'Connection refused while running JCMsolve with parameter %s.' 
          % command)
    
    return python_socket, signature, url
    
def _CommandLength2ByteArray(command):
    """
    Returns a bytearray of length 4, which encodes the length of the command
    which should be send to the daemon, as it expects to get the command length
    before execution.
    """
    return bytearray( struct.pack("I", len(command)) )


def _recv_size(the_socket):
    """
    Receives a message of a defined size, encoded in the first 4 bytes of the
    message itself. Based on the recipe presented on:
                        http://code.activestate.com/recipes/408859/
    """
    #data length is packed into 4 bytes
    
    total_len = 0
    total_data = bytearray()
    size = sys.maxsize
    size_data = bytearray()
    recv_size = 4#8192
    t0 = time.time() # measure time in this process
    while total_len < size:
        sock_data = the_socket.recv(recv_size)
        if not total_data:
            if len(sock_data) >= 4:
                size_data.extend(sock_data)
                size = struct.unpack('I', size_data[:4])[0]
                recv_size = size
                if recv_size > 524288:
                    recv_size=524288
                total_data.extend( size_data[4:] )
            else:
                size_data.extend(sock_data)
        else:
            total_data.extend( sock_data )
        total_len = len(total_data) #sum([len(i) for i in total_data ])
        t1 = time.time() - t0
        if t1 > 300:
            warning("""Breaking after waiting {0}s 
            for communication.""".format(t1))
            break
        
    return total_data.decode()
