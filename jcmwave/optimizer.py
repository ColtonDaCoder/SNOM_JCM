#!/usr/bin/env python
# ==============================================================================
#
# Copyright(C) 2018 JCMwave GmbH, Berlin.
# All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Philipp Schneider
# Date:           03/03/18
#
# ==============================================================================

__doc__ = """
The module ``jcmwave.optimizer`` allows for controlling the optimization server and for creating
new optimization studies. In the most cases it is sufficient to create a new
:class:`~jcmwave.client.Study` instance by calling :func:`~jcmwave.optimizer.create_study`. For example::

    domain = [
       {'name': 'x1', 'type': 'continuous', 'domain': (-1.5,1.5)}, 
       {'name': 'x2', 'type': 'continuous', 'domain': (-1.5,1.5)},
    ]
    study = jcmwave.optimizer.create_study(domain=domain, name='example')

.. note:: The ``study`` object allows for setting up the optimization itself. 
   For more information, see :class:`jcmwave.client.Study`.

"""


# Imports
# ------------------------------------------------------------------------------
import os
import jcmwave
import jcmwave.__private as __private
import json
import tempfile
import time
from subprocess import Popen
from .client import Client, Observation

def startup(port = None, persistent = False):
    """Starts the optimizer on a specific host and port

       :param str port: The port that the optimization server is listening on. 
       :param bool persistent: In persistent mode the optimization server will stay alive 
           after Python has closed. Otherwise the server will shut down automatically. 
    """
    # Check if JCMoptimizer binary location is known...
    if not 'JCMoptimizer' in dir(__private): jcmwave.startup() 
    elif __private.JCMoptimizer is None: jcmwave.startup()
    
    # Generate temporary files for errors and log
    error_file = tempfile.TemporaryFile()
    log_file = tempfile.TemporaryFile()
    
    # Start JCMoptimizer
    cmd = ['"{}"'.format(__private.JCMoptimizer)]
    if port is not None: cmd.append('--port {}'.format(port))
    cmd.append('--print_json')
    if not persistent: cmd.append('--calling_pid {}'.format(os.getpid()))
    cmd=' '.join(cmd)
    close_fds = os.name!='nt'
    p = Popen(cmd, shell=True, stdout=log_file, stderr=error_file, close_fds=close_fds, universal_newlines=True, bufsize=1)

    # Poll process for new output until first line with port information
    line = ""
    for _ in range(100): #wait for 10 seconds for startup of optimizer
        log_file.seek(0)
        for line in iter(log_file.readline, b''):
            if line[:17]==b'{"optimizer_port"':
                break
        else:
            time.sleep(0.1)
            continue
        break
    
    try: info = json.loads(line)
    except:        
        log_file.seek(0)
        error_file.seek(0)
        log = [l.decode() for l in log_file.readlines()]
        errs = [l.decode() for l in error_file.readlines()]
        raise EnvironmentError('Could not start optimization server. Server response: {}'.format(''.join(log+errs)))
    
    __private.optimizer = info
    __private.optimizer_process=p

def check(warn=True):
    """Checks whether there is a running optimization server.

       :param bool warn: Shown warning messages.
    """
    if __private.optimizer is None:
        if warn: __private.warning('The optimization server was not started.')
        return False
    else: #try to connect to server
        port = __private.optimizer['optimizer_port']
        try: c = Client('http://localhost:{}'.format(port), check=True)
        except EnvironmentError as e:
            if warn: __private.warning(str(e))
            return False
    return True

    
def client(port = None):
    """Creates a :class:`jcmwave.client.Client` instance, that can communicate with an optimization server.
    If no server is running, it will be started automatically. 

    .. note:: This function is useful if you 
       want to start the optimization server on another computer. In this case you can do the following:

       1. Login to the other computer
       2. Start the optimization server manually by calling 
          ``$JCMROOT/ThirdPartySupport/Python/bin/JCMoptimizer``. 
       3. Forward the ports of the optimizer to your local computer, e.g. by calling
          ``ssh -NL 4554:localhost:4554 user@remotehost``
       4. Create a :class:`jcmwave.client.Client` instance: ``c=jcmwave.optimizer.client(port=4554)``.
       5. Create a new study by calling ``c.create_study()`` 
          (see :func:`jcmwave.client.Client.create_study`).

    :param port: The port that the optimization server is listening on. 
        If no port is specified, the client communicates with the server that was 
        started by calling :func:`~jcmwave.optimizer.startup`. 

    """
    if port is None:
        if not check(warn=False): startup()
        port = __private.optimizer['optimizer_port']
        
    return Client('http://localhost:{}'.format(port), check=False)

def create_study(**kwargs):
    """
    Creates a new optimization ``study`` object. 

    .. note:: For a description of the input arguments, see :class:`jcmwave.client.Client.create_study`.
    .. note:: For a description of the ``Study`` class, see :class:`jcmwave.client.Study`.
    """

    if not check(warn=False): startup()
    port = __private.optimizer['optimizer_port']

    c = Client('http://localhost:{}'.format(port), check=False)
    return c.create_study(**kwargs)

#Copy docstring from Client class
docstring = Client.create_study.__doc__
docstring = docstring.replace('client.create_study','jcmwave.optimizer.create_study')
docstring = docstring.replace('client.Study','jcmwave.client.Study')
create_study.__doc__ = docstring

def create_benchmark(**kwargs):
    """
    Creates a new ``benchmark`` object. 

    .. note:: For a description of the input arguments, see :class:`jcmwave.client.Client.create_benchmark`.
    .. note:: For a description of the ``Benchmark`` class, see :class:`jcmwave.client.Benchmark`.
    """

    if not check(warn=False): startup()
    port = __private.optimizer['optimizer_port']

    c = Client('http://localhost:{}'.format(port), check=False)
    return c.create_benchmark(**kwargs)

#Copy docstring from Client class
docstring2 = Client.create_benchmark.__doc__
docstring2 = docstring2.replace('client.create_benchmark','jcmwave.optimizer.create_benchmark')
docstring2 = docstring2.replace('client.Benchmark','jcmwave.client.Benchmark')
create_benchmark.__doc__ = docstring2

def shutdown(port = None, force=False):
    """
    Shuts down the optimization server

    :param port: The port where the optimization server is running. If not port is 
         provided, the server started by calling :func:`~jcmwave.optimizer.startup` is closed.
    :param bool force: If True the optimization server is closed even if a study
         is not yet finished.
    """    
    c = client(port)
    c.shutdown_server(force)
    __private.optimizer = None
