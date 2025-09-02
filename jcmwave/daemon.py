#!/usr/bin/env python

# ==============================================================================
#
# Copyright(C) 2013 JCMwave GmbH, Berlin.
# All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Carlo Barth, Martin Hammerschidt 
#                 (based on MATLAB-version by Lin Zschiedrich)
# Date:           27/05/23
#
# ==============================================================================


# Imports
# ------------------------------------------------------------------------------
from __future__ import print_function
import jcmwave
import jcmwave.__private as __private
from jcmwave.data_tree import data_branch as db, data_primitives as dp
import numpy as np
import os
import pprint
import re # regular expression parsing
import socket # TCP communication
import struct
import subprocess
import sys
import tempfile
import time
import shutil
import string



# Name space helper class
# ------------------------------------------------------------------------------
class NameSpaceHelper(object):
    """
    Only needed for Matlab-like syntax. E.g.
        foo = NameSpaceHelper()
        foo.bar = []
    """
    pass


# Function definitions
# ------------------------------------------------------------------------------

def WriteTreeDir(treeDir, indent=0):
    """
    Converts a python data tree to a formatted string, as it is expected by
    the JCMdaemon.
    """
    returnString = ''
    primitiveDataMap = treeDir.GetPrimitives()
    for primIter in primitiveDataMap.items():
        returnString += '\n' + 2*indent*' ' + str(primIter[0][0])
        returnString += ' = ' + primIter[1].Write()
    branchDataMap = treeDir.GetDirs()
    for branchIter in branchDataMap.items():
        branchName = branchIter[0][0]
        returnString += '\n' + 2*indent*' ' + branchName + ' {'
        returnString += WriteTreeDir(branchIter[1], indent+1) # recursive call
        returnString += '\n' + 2*indent*' ' + '}'
    return returnString

def run_command(datatree, get_answer=True):
    """
    Runs an arbitrary command encoded as a data tree using the daemon.
    """
    # Check if there is a running daemon and a socket
    if daemonCheck():
        socket = __private.JCMdaemon.python_socket
    else:
        return
    
    # Generate a 'root'- and a 'Task'-data tree and add the actual data tree
    root = db.TreeDir.Create('root')
    task = db.TreeDir.Create('Task')
    task.AddTreeDir(datatree)
    root.AddTreeDir(task)
    
    # Daemon Interaction
    command = WriteTreeDir(root) # generate string from data tree
    return __private.send_message(socket, command, get_answer)  
        

def daemonCheck(warn=True):
    """
    Checks wether there is a running daemon and a socket.
    """
    if not hasattr(__private, 'JCMdaemon'):
        if warn: __private.warning('No running daemon found.')
        return False
    elif not hasattr(__private.JCMdaemon, 'python_socket'):
        if warn: __private.warning('No socket found.')
        return False
    else:
        return True


def status(printOut = False):
    """
    Sends the 'DaemonStatus'-command to the daemon and returns the status
    information.
    """
    # Check if there is a running daemon and a socket
    if daemonCheck():
        socket = __private.JCMdaemon.python_socket
    else:
        return
    
    # Generate the data tree which encodes the task
    datatree = db.TreeDir.Create('DaemonStatus')
    
    # Pass it to the daemon
    daemonAnswer = run_command(datatree)
    
    # Execute the python commands which have been returned by the daemon
    lines = daemonAnswer.split('\n')
    jcmNameSpaceL=locals()
    for line in lines[1:-3]:
        exec(line,globals(),jcmNameSpaceL)
    try:
        s1=jcmNameSpaceL['s1']
        s2=jcmNameSpaceL['s2']
    except:
        raise EnvironmentError('Error in jcm_wave_daemon_status: received erroneous data.')
        
    s1['Jobs'] = s2
    if printOut: pprint.pprint( s1, width=80)
    return s1


def startup(port=None):
    """
    Starts the daemon on a local machine.
    
    :param port: The port that the JCMdaemon is listening on. 
        If no port is specified, the JCMdaemon chooses a port automatically. 
    """
    # Check if all JCMwave binary locations are known...
    if not 'JCMsolve' in dir(__private):
        jcmwave.startup() # ...load them if not
    elif __private.JCMsolve == None:
        jcmwave.startup()
    
    # Generate the namespace for JCMdaemon
    J = NameSpaceHelper()    
    J.python_socket,J.signature,J.url = __private.run_command(
        JCMsolve=__private.JCMsolve, 
        command='--start_daemon',
        calling_pid=os.getpid(),
        defaultPort=port
    )
    J.cachedIDs = dict();
    J.temporaryIDs = set() #  of job ids with temporary data storage
    __private.JCMdaemon = J
   
def install_remote_environment(Hostname = 'localhost',
                      JCMROOT = None,
                      Login = '',
                      SSHClient = None,
                      SSHAgentForwarding = None,
                      SSHTimeOut = None,
                      PEMFile = None,
                      LicenseServerPort = 8992,
                      IncludePython = False         
):
    """
    Instals a minimal JCMsuite environment on a remote host. 
    Example for setting up and using a blank Ubuntu AWS (Amazon Web Service) instance::

        kwargs = dict(Hostname = 'ec2-11-222-33-44.us-west-2.compute.amazonaws.com', 
                      Login = 'ec2-user',
                      JCMROOT = '/home/ec2-user/bin/JCMsuite',
                      PEMFile = '~/.ssh/KeyPairAmazon.pem',
                      LicenseServerPort = 8992)
        jcmwave.daemon.install_remote_environment(**kwargs)
        jcmwave.daemon.add_workstation(Multiplicity = 12, **kwargs)

    .. note:: The installation process can take a few minutes. It can be therefore 
        practical to store the machine image afterwards.
    
    :param str Hostname: host name of the remote computer
        To form a login chain concatenate the hostnames with
        `;` separators, i.e ``gateway.com;maxwell``
    :param str JCMROOT: JCMsuite installation path on remote computer 
        default: same directory as local installation
    :param str PEMFile: File with private ssh-key for establishing a ssh 
        connection, e.g. `~/.ssh/id_rsa` (optional). 
    :param str Login: Login name to the remote computer
        For a login chain concatenate the user names with
        `;` separators, i.e ``user1;user2``
    :param str SSHClient:  ssh client used to establish a secure connection to the
        remote machine. As a default the system ssh client
        is used (if not available on Windows Putty's plink is used)
        For a login chain concatenate ssh clients with
        ';' separators, i.e 'plink;ssh'
    :param str SSHAgentForwarding:  Enables forwarding of the authentication agent connection. 
        (boolean, default False)
    :param str SSHTimeOut: Timeout for establishing the ssh connection (default 6s)
    :param int LicenseServerPort: The remote installation looks for a license 
        server at `localhost:XXXX`, where XXX is the LicenseServerPort. 
        Call :func:`~.add_workstation` with the same value to forward the
        local license server to this port on the remote machine. default: 8992
    :param bool IncludePython: Set to True to include Python in the installation.
        In many cases the remote environment does not require a Python 
        installation (size about 1GB). Only if, e.g., user-defined field sources, 
        material tensors or integration densities are provided as Python expressions, 
        Python has to be included in the installation. The use of embedded scripting 
        does not require Python on the remote host.

    .. warning:: The remote installation works only if both the local machine and 
          the remote host run Linux. If the local machine runs Microsoft Windows, 
          the installation on the remote host must be performed manually 
          (i.e. by uploading the installation script to the remote machine and 
          running the installation.)

    """
    # Type-checking
    if not isinstance(Hostname, str):
        raise TypeError('Hostname -> string expected.')
    if (JCMROOT is not None) and not isinstance(JCMROOT, str):
        raise TypeError('JCMROOT -> file path expected.')
    if not isinstance(Login, str):
        raise TypeError('Login -> string expected.')
    if (SSHClient is not None) and not isinstance(SSHClient, str):
        raise TypeError('SSHClient -> string expected.')
    if (SSHAgentForwarding is not None) and not isinstance(SSHAgentForwarding, bool):
        raise TypeError('SSHAgentForwarding -> bool expected.')
    if (SSHTimeOut is not None) and not (isinstance(SSHTimeOut, int) and SSHTimeOut>0):
        raise TypeError('SSHTimeOut -> integer > 1 expected.')
    if not (isinstance(LicenseServerPort,int) and LicenseServerPort > 0):
        raise TypeError('LicenseServerPort -> Positive integer argument expected.')
    IncludePython = 'Yes' if IncludePython else 'No'

    # Check if there is a running daemon and a socket
    if not daemonCheck(warn=False):
        startup()
    
    # Generate the data tree
    datatree = db.TreeDir.Create('InstallRemoteEnvironment')
    datatree.AddPrimitive("Hostname", dp.StringPrimitive(True, Hostname))
    datatree.AddPrimitive("Login", dp.StringPrimitive(True, Login))
    if (SSHClient is not None):
        datatree.AddPrimitive("SSHClient", dp.StringPrimitive(True, SSHClient))
    if (SSHAgentForwarding is not None):
        datatree.AddPrimitive("SSHAgentForwarding", dp.StringPrimitive('yes' if (SSHAgentForwarding) else 'no'))
    if (SSHTimeOut is not None):
        datatree.AddPrimitive("SSHTimeOut", dp.NumberPrimitive(SSHTimeOut, int))
    if JCMROOT is not None:
        datatree.AddPrimitive("JCMROOT", dp.StringPrimitive(True, JCMROOT))
    datatree.AddPrimitive("IncludePython", dp.StringPrimitive(True, IncludePython))
    datatree.AddPrimitive("LicenseServerPort", dp.NumberPrimitive(LicenseServerPort, int))
 
    if not PEMFile is None:
      datatree.AddPrimitive("PEMFile", dp.StringPrimitive(True, os.path.abspath(PEMFile)))

    datatree.AddPrimitive("Step", dp.StringPrimitive(True, "minify"))
    print('Minifying local installation...', end=' ')
    sys.stdout.flush()    
    daemonAnswer = extractReturnValue(run_command(datatree))
    print('done')
    datatree.AddPrimitive("TarPath", dp.StringPrimitive(True, daemonAnswer['TarPath']))
    datatree.SetPrimitive("Step", dp.StringPrimitive(True, "transfer"))
    size = os.path.getsize(daemonAnswer['TarPath'])
    print('Transferring installation files to host ({}MB)...'.format(int(size/1024/1024)),end=' ')
    sys.stdout.flush()    
    extractReturnValue(run_command(datatree))
    print('done')
    datatree.SetPrimitive("Step", dp.StringPrimitive(True, "install"))
    print('Installing minimal version of JCMsuite on host...',end=' ')
    sys.stdout.flush()    
    extractReturnValue(run_command(datatree))
    print('done')
    


def add_workstation(Hostname = 'localhost',
                      JCMROOT = None,
                      Login = '',
                      SSHClient = None,
                      SSHAgentForwarding = None,
                      SSHTimeOut = None,
                      PEMFile = None,
                      Multiplicity = 1,
                      NThreads = 1,
                      WorkingDir = '',
                      OOCDir = None, 
                      MaxCoreSize = None, 
                      MemoryLimit = None,
                      LicenseServerPort = None):
    """
    Adds a new workstation. Example::
    
        jcmwave.daemon.add_workstation(Hostname='maxwell', Multiplicity=4, NThreads=4)
    
    :param str Hostname: host name of the remote computer
        To form a login chain concatenate the hostnames with
        `;` separators, i.e ``gateway.com;maxwell``
    :param str JCMROOT: JCMsuite installation path on remote computer 
        default: same directory as local installation
    :param str PEMFile: File with private ssh-key for establishing a ssh 
        connection, e.g. `~/.ssh/id_rsa` (optional). 
    :param str Login: Login name to the remote computer
        For a login chain concatenate the user names with
        `;` separators, i.e ``user1;user2``
    :param str SSHClient:  ssh client used to establish a secure connection to the
        remote machine. As a default the system ssh client
        is used (if not available on Windows Putty's plink is used)
        For a login chain concatenate ssh clients with
        ';' separators, i.e 'plink;ssh'
    :param str SSHAgentForwarding:  Enables forwarding of the authentication agent connection. 
        (boolean, default False)
    :param str SSHTimeOut: Timeout for establishing the ssh connection (default 6s)
    :param int Multiplicity: allow for multiply simultaneous use of the resource
        default: 1 (single use)
    :param int NThreads: number of threads used by one job on the remote computer
    :param str WorkingDir: Directory used by JCMsuite to place temporary files. 
    :param str OOCDir: swapping directory for out-of-core data 
    :param int MaxCoreSize: restricts maximum core RAM usage (requires setting
        of swapping directory OOCDIR)
    :param int MemoryLimit: maximum RAM usage in MB (aborts jobs if exceeded)
    :param int LicenseServerPort: If the remote machine cannot reach the local
        license server (e.g. a cloud instance), it can be configured to look for
        the license server at `localhost:XXXX`. Then, LicenseServerPort must be equal
        to XXXX. default: No port forwarding.

    .. warning:: Adding a machine recursively increases the number of 
          simultaneously running jobs on this machine.   
    """
    # Type-checking
    if not isinstance(Hostname, str):
        raise TypeError('Hostname -> string expected.')
    if (JCMROOT is not None) and not isinstance(JCMROOT, str):
        raise TypeError('JCMROOT -> file path expected.')
    if not isinstance(Login, str):
        raise TypeError('Login -> string expected.')
    if (SSHClient is not None) and not isinstance(SSHClient, str):
        raise TypeError('SSHClient -> string expected.')
    if (SSHAgentForwarding is not None) and not isinstance(SSHAgentForwarding, bool):
        raise TypeError('SSHAgentForwarding -> bool expected.')
    if (SSHTimeOut is not None) and not (isinstance(SSHTimeOut, int) and SSHTimeOut>0):
        raise TypeError('SSHTimeOut -> integer > 1 expected.')
    if not isinstance(Multiplicity, int) or not Multiplicity >= 0:
        raise TypeError('Multiplicity -> non-negative integer expected.')
    if not isinstance(NThreads, int) or not NThreads >= 0:
        raise TypeError('NThreads -> non-negative integer expected.')
    if not isinstance(WorkingDir, str):
        raise TypeError('WorkingDir -> file path expected.')
    if not OOCDir is None:
       if not isinstance(OOCDir,str): 
          raise TypeError('OOCDir -> directory path expected.');
       if (not os.path.isdir(OOCDir)):
          raise TypeError('OOCDir -> not a valid directory path');
    if not MaxCoreSize is None:
       if (not isinstance(MaxCoreSize,int)) or (MaxCoreSize<500):
          raise TypeError('MaxCoreSize -> integer argument >= 500 expected.')
    if not MemoryLimit is None:
       if (not isinstance(MemoryLimit,int)) or (MemoryLimit<1):
          raise TypeError('MemoryLimit -> Positive integer argument expected.')
    if (LicenseServerPort is not None and not (
            isinstance(LicenseServerPort,int) and LicenseServerPort > 0)):
        raise TypeError('LicenseServerPort -> Positive integer argument expected.')
    
    
    # Check if there is a running daemon and a socket
    if not daemonCheck(warn=False):
        startup()
    
    # Generate the data tree
    datatree = db.TreeDir.Create('RegisterResource')
    datatree.AddPrimitive("Hostname", dp.StringPrimitive(True, Hostname))
    datatree.AddPrimitive("Login", dp.StringPrimitive(True, Login))
    if (SSHClient is not None): 
        datatree.AddPrimitive("SSHClient", dp.StringPrimitive(True, SSHClient))
    if (SSHAgentForwarding is not None):
        datatree.AddPrimitive("SSHAgentForwarding", dp.StringPrimitive(False, 'yes' if (SSHAgentForwarding) else 'no'))
    if (SSHTimeOut is not None):
        datatree.AddPrimitive("SSHTimeOut", dp.NumberPrimitive(SSHTimeOut, int))
    if JCMROOT is not None:
        datatree.AddPrimitive("JCMROOT", dp.StringPrimitive(True, JCMROOT))
    datatree.AddPrimitive("Multiplicity", dp.NumberPrimitive(Multiplicity, int))
     
    wStation = db.TreeDir.Create('Workstation')
    wStation.AddPrimitive("NThreads", dp.NumberPrimitive(NThreads, int))
    wStation.AddPrimitive("WorkingDir", dp.StringPrimitive(True, WorkingDir))
    
    if not OOCDir is None:
      wStation.AddPrimitive("OOCDir", dp.StringPrimitive(True, OOCDir))
    if not MaxCoreSize is None:
      wStation.AddPrimitive("MaxCoreSize", dp.NumberPrimitive(MaxCoreSize, int))
    if not MemoryLimit is None:
      wStation.AddPrimitive("MemoryLimit", dp.NumberPrimitive(MemoryLimit, int))
    if not PEMFile is None:
      datatree.AddPrimitive("PEMFile", dp.StringPrimitive(True, os.path.abspath(PEMFile)))
    if not LicenseServerPort is None:
      datatree.AddPrimitive("LicenseServerPort", dp.NumberPrimitive(LicenseServerPort, int))
                            
    datatree.AddTreeDir(wStation)
    daemonAnswer = run_command(datatree)
    return extractReturnValue(daemonAnswer)


def add_cluster(Nodes,
                Hostname = 'localhost',
                      JCMROOT = None,
                      Login = '',
                      SSHClient = None,
                      SSHAgentForwarding = None,
                      SSHTimeOut = None,
                      PEMFile = None,
                      Multiplicity = 1,
                      NThreads = 1,
                      WorkingDir = '',
                      OOCDir = None, 
                      MaxCoreSize = None, 
                      LicenseServerPort = None):
    """
    Adds a new computation cluster. Example::
    
        cluster=[{'Hostname': 'computer1'},{'Hostname': 'computer2'}]
        jcmwave.daemon.add_cluster(Hostname='Hostname', 'computer1', Nodes=cluster)
    
    :param str Hostname: host name of the remote cluster access point
        To form a login chain concatenate the hostnames with
        `;` separators, i.e ``gateway.com;maxwell``
    :param str JCMROOT: JCMsuite installation path on remote computer 
        default: same directory as local installation
    :param str PEMFile: File with private ssh-key for establishing a ssh 
        connection, e.g. `~/.ssh/id_rsa` (optional). 
    :param str Login: Login name to the remote computer
        For a login chain concatenate the user names with
        `;` separators, i.e ``user1;user2``
    :param str SSHClient:  ssh client used to establish a secure connection to the
        remote machine. As a default the system ssh client
        is used (if not available on Windows Putty's plink is used)
        For a login chain concatenate ssh clients with
        ';' separators, i.e 'plink;ssh'
    :param str SSHAgentForwarding:  Enables forwarding of the authentication agent connection. 
        (boolean, default False)
    :param str SSHTimeOut: Timeout for establishing the ssh connection (default 6s)
    :param int Multiplicity: allow for multiply simultaneous use of the resource
        default: 1 (single use)
    :param int NThreads: number of threads used by one job on the remote computer
    :param str WorkingDir: Directory used by JCMsuite to place temporary files. 
    :param str OOCDir: swapping directory for out-of-core data 
    :param int MaxCoreSize: restricts maximum core RAM usage (requires setting
        of swapping directory OOCDIR)
    :param list Nodes: List for the specification of the computer nodes of the cluster.
        An entry is a dictionary with keys the following key-value pairs:
            'Hostname' -> hostname (or ip-address) of the cluster node as seen from the cluster access point
            'JCMROOT' -> JCMsuite installation path on this cluster ode  
        As default None is also accepted (as JCMROOT the value of the access point is used)
    :param int LicenseServerPort: If the remote machine cannot reach the local
        license server (e.g. a cloud instance), it can be configured to look for
        the license server at `localhost:XXXX`. Then, LicenseServerPort must be equal
        to XXXX. default: No port forwarding.

    .. warning:: Adding a machine recursively increases the number of 
          simultaneously running jobs on this machine.   
    """
    # Type-checking
    if not isinstance(Hostname, str):
        raise TypeError('Hostname -> string expected.')
    if (JCMROOT is not None) and not isinstance(JCMROOT, str):
        raise TypeError('JCMROOT -> file path expected.')
    if not isinstance(Login, str):
        raise TypeError('Login -> string expected.')
    if (SSHClient is not None) and not isinstance(SSHClient, str):
        raise TypeError('SSHClient -> string expected.')
    if (SSHAgentForwarding is not None) and not isinstance(SSHAgentForwarding, bool):
        raise TypeError('SSHAgentForwarding -> bool expected.')
    if (SSHTimeOut is not None) and not (isinstance(SSHTimeOut, int) and SSHTimeOut>0):
        raise TypeError('SSHTimeOut -> integer > 1 expected.')
    if not isinstance(Multiplicity, int) or not Multiplicity >= 0:
        raise TypeError('Multiplicity -> non-negative integer expected.')
    if not isinstance(NThreads, int) or not NThreads >= 0:
        raise TypeError('NThreads -> non-negative integer expected.')
    if not isinstance(WorkingDir, str):
        raise TypeError('WorkingDir -> file path expected.')
    if not OOCDir is None:
       if not isinstance(OOCDir,str): 
          raise TypeError('OOCDir -> directory path expected.');
       if (not os.path.isdir(OOCDir)):
          raise TypeError('OOCDir -> not a valid directory path');
    if not MaxCoreSize is None:
       if (not isinstance(MaxCoreSize,int)) or (MaxCoreSize<500):
          raise TypeError('MaxCoreSize -> integer argument >=500 expected.')
    if (LicenseServerPort is not None and not (
            isinstance(LicenseServerPort,int) and LicenseServerPort > 0)):
        raise TypeError('LicenseServerPort -> Positive integer argument expected.')
    if not isinstance(Nodes, list):
        raise TypeError('Nodes -> list expected.')

    for iNode, node in enumerate(Nodes):
        if not isinstance(node, dict):
            raise TypeError('Nodes[%d] -> not a dictionary.' % (iNode))
        for key in node:
            if (key == 'Hostname'):
                if not isinstance(node[key], str):
                    raise TypeError("Nodes[%d]['%s'] -> invalid value (string expected)." % (iNode, key))
            elif (key == 'JCMROOT'):
                if not isinstance(node[key], str):
                    raise TypeError("Nodes[%d]['%s'] -> invalid value (string expected)." % (iNode, key))
            elif (key == 'MemoryLimit'):
                if not isinstance(node[key], int):
                    raise TypeError("Nodes[%d]['%s'] -> invalid value (integer expected)." % (iNode, key))
            else:
                raise TypeError('Nodes[%d] -> invalid key "%s".' % (iNode, key))
    
    # Check if there is a running daemon and a socket
    if not daemonCheck(warn=False):
        startup()
    
    # Generate the data tree
    datatree = db.TreeDir.Create('RegisterResource')
    datatree.AddPrimitive("Hostname", dp.StringPrimitive(True, Hostname))
    datatree.AddPrimitive("Login", dp.StringPrimitive(True, Login))
    if (SSHClient is not None): 
        datatree.AddPrimitive("SSHClient", dp.StringPrimitive(True, SSHClient))
    if (SSHAgentForwarding is not None):
        datatree.AddPrimitive("SSHAgentForwarding", dp.StringPrimitive(False, 'yes' if (SSHAgentForwarding) else 'no'))
    if (SSHTimeOut is not None):
        datatree.AddPrimitive("SSHTimeOut", dp.NumberPrimitive(SSHTimeOut, int))
    if JCMROOT is not None:
        datatree.AddPrimitive("JCMROOT", dp.StringPrimitive(True, JCMROOT))
    datatree.AddPrimitive("Multiplicity", dp.NumberPrimitive(Multiplicity, int))
     
    cluster = db.TreeDir.Create('Cluster')
    cluster.AddPrimitive("NThreads", dp.NumberPrimitive(NThreads, int))
    cluster.AddPrimitive("WorkingDir", dp.StringPrimitive(True, WorkingDir))
    
    for node in Nodes:
        nodeTree=db.TreeDir.Create('Node')
        for key in node:
            if (key=='JCMROOT' or key=='Hostname'):
              nodeTree.AddPrimitive(key, dp.StringPrimitive(True, node[key]))
            if (key=='MemoryLimit'):
              nodeTree.AddPrimitive(key, dp.NumberPrimitive(node[key], int))
        cluster.AddTreeDir(nodeTree)

    if not OOCDir is None:
      cluster.AddPrimitive("OOCDir", dp.StringPrimitive(True, OOCDir))
    if not MaxCoreSize is None:
      cluster.AddPrimitive("MaxCoreSize", dp.NumberPrimitive(MaxCoreSize, int))
    
    if not PEMFile is None:
      datatree.AddPrimitive("PEMFile", dp.StringPrimitive(True, os.path.abspath(PEMFile)))
    if not LicenseServerPort is None:
      datatree.AddPrimitive("LicenseServerPort", dp.NumberPrimitive(LicenseServerPort, int))
                            
    datatree.AddTreeDir(cluster)
    daemonAnswer = run_command(datatree)
    return extractReturnValue(daemonAnswer)


def extractReturnValue(string):
    string = string.replace("\\","\\\\")
    jcmNameSpaceL=locals()
    exec(string,globals(),jcmNameSpaceL)
    s0 = jcmNameSpaceL['s0']
    if len(s0.keys()) == 0:
        return
    if not 'ReturnValue' in s0.keys():
        if 'Error' in s0.keys():
            raise Exception('Error: ' + s0['Error']['Message'])
            return
    return s0['ReturnValue']


def add_queue(Hostname = 'localhost',
              JCMROOT = None,
              Login = '',
              SSHClient = None,
              SSHAgentForwarding = None,
              SSHTimeOut = None,
              Multiplicity = 10,
              Type = 'Slurm',
              JobName = '',
              PartitionName = '',
              NNodes = None,
              NTasks = None,
              NTasksPerNode = None,
              NodeList = '',
              ExcludeNode = '',
              WorkingDir = '',
              NThreads = 1,
              Time = None,
              Features = None,  
              Exclusive = None,             
              MemoryPerJob = None,
              OOCDir = None, 
              MaxCoreSize = None,
              Environment = None):
    """
    Adds a new queue with a given multiplicity. Example::
    
        jcmwave.daemon.add_queue(Hostname='localhost', Multiplicity=24, NThreads=4)
    
    :param str Hostname: host name of the (remote) login node of the queue.
        To form a login chain concatenate the hostnames with
        `;` separators, i.e ``gateway.com;maxwell``
    :param str JCMROOT: JCMsuite installation path on computing nodes of the queue.
        default: same directory as local installation
    :param str Login: Login name to the (remote) login node of the queue
        For a login chain concatenate the user names with
        `;` separators, i.e ``user1;user2``
    :param str SSHClient:  ssh client used to establish a secure connection to the
        remote machine. As a default the system ssh client
        is used (if not available on Windows Putty's plink is used)
        For a login chain concatenate ssh clients with
        ';' separators, i.e 'plink;ssh'
    :param str SSHAgentForwarding:  Enables forwarding of the authentication agent connection. 
        (boolean, default False)
    :param str SSHTimeOut: Timeout for establishing the ssh connection (default 6s)
    :param int Multiplicity: allow for multiply simultaneous submission of jobs to the queue
        default: 10 
    :param str Type: Determines type of batch queue. Possible values are: Slurm.
        default: Slurm
    :param str PartitionName: Name of the slurm partition you want to add 
    :param str NNodes: number of nodes allocated for each job to run a cluster parallel problem
    :param str NTasks: number of tasks allocated for each job to run a cluster parallel problem
    :param str NTasksPerNode: (maximum) number of taks per node
    :param str WorkingDir: Directory used by JCMsuite to place temporary files. 
        Project files are copied as well if the project directory 
        is not shared by the login nodes and the nodes of the queue. 
        This directory must be accessible by any node of the queue, 
        i.e. a directory on a shared filesystem. 
    :param str Features: Constraints job allocation to nodes of the cluster with the selected features.
    :param str NodeList: Limit job execution to a specific node of the cluster.
    :param str ExcludeNode: Exclude a node of a partition from executing jobs.
        Multiple nodes can be entered as a comma separated list containing no spaces, i.e. maxwell1,maxwell2,... or
        as a range of nodes, i.e. maxwell[1-3].Setting a node
        list and excluding a node are mutually exclusive.
    :param str OOCDir: swapping directory for out-of-core data 
    :param int MaxCoreSize: restricts maximum core RAM usage (requires setting
        of swapping directory OOCDIR)  
    :param float MemoryPerJob: Reserve at least MemPerCPU MB of RAM for every job that is run on this allocation
        (for a distributed job running on multiple nodes this is the maximum memory usage per node)Environment   
    :param str Environment: list of environment variables (separated by white spaces)

    .. warning:: Adding a job queue recursively increases the number of
          simultaneously submitted jobs in this queue.   

    """
    # Type-checking
    if not isinstance(Hostname, str):
        raise TypeError('Hostname -> string expected.')
    if (JCMROOT is not None) and not isinstance(JCMROOT, str):
        raise TypeError('JCMROOT -> file path expected.')
    if not isinstance(Login, str):
        raise TypeError('Login -> string expected.')
    if (SSHClient is not None) and not isinstance(SSHClient, str):
        raise TypeError('SSHClient -> string expected.')
    if (SSHAgentForwarding is not None) and not isinstance(SSHAgentForwarding, bool):
        raise TypeError('SSHAgentForwarding -> bool expected.')
    if (SSHTimeOut is not None) and not (isinstance(SSHTimeOut, int) and SSHTimeOut>0):
        raise TypeError('SSHTimeOut -> integer > 1 expected.')
    if not isinstance(Multiplicity, int) or not Multiplicity >= 0:
        raise TypeError('Multiplicity -> non-negative integer expected.')
    if not isinstance(Type, str) or not Type == 'Slurm':
        raise TypeError('Type -> string expected.')
    if not isinstance(JobName, str):
        raise TypeError('JobName -> string expected.')
    if not isinstance(PartitionName, str):
        raise TypeError('PartitionName -> string expected.')
    if not NNodes is None:
      if not isinstance(NNodes, int) or not NNodes>=1:
          raise TypeError('NNodes -> positive integer expected.')
    if not NTasks is None:
      if not isinstance(NTasks, int) or not NTasks>=1:
          raise TypeError('NTasks -> positive integer expected.')
    if not NTasksPerNode is None:
      if not isinstance(NTasksPerNode, int) or not NTasksPerNode>=1:
          raise TypeError('NTasksPerNode -> positive integer expected.')
    if not isinstance(NodeList, str):
        raise TypeError('NodeList -> string expected.')
    if not isinstance(ExcludeNode, str):
        raise TypeError('ExcludeNode -> string expected.')
    if not isinstance(WorkingDir, str):
        raise TypeError('WorkingDir -> file path expected.')
    if not isinstance(NThreads, int) or not NThreads >= 0:
        raise TypeError('NThreads -> non-negative integer expected.')
    if not OOCDir is None:
       if not isinstance(OOCDir,str): 
          raise TypeError('OOCDir -> directory path expected.');
       if (not os.path.isdir(OOCDir)):
          raise TypeError('OOCDir -> not a valid directory path');
    if not MaxCoreSize is None:
       if (not isinstance(MaxCoreSize,int)) or (MaxCoreSize<500):
          raise TypeError('MaxCoreSize -> integer argument >=500 expected.')
    if Time is not None:
        if not isinstance(Time, float) or not Time >= 0.0:
            raise TypeError('Time -> non-negative float expected.')
    if (Exclusive is not None) and not isinstance(Exclusive, bool):
        raise TypeError('Exclusive -> bool expected.')
    if (Features is not None) and not isinstance(Features, str):
        raise TypeError('Features -> string expected.')
    if (Environment is not None) and not isinstance(Environment, str):
        raise TypeError('Environment -> string expected.')
    if MemoryPerJob is not None:
        if not isinstance(MemoryPerJob,float) or not MemoryPerJob >= 0.0 :
            raise TypeError('MemoryPerJob ->  non-negative float expected.')
    
    # Check if there is a running daemon and a socket
    if not daemonCheck(warn=False):
        startup()
    
    # Generate the data tree
    datatree = db.TreeDir.Create('RegisterResource')
    datatree.AddPrimitive("Hostname", dp.StringPrimitive(True, Hostname))
    if JCMROOT is not None: 
        datatree.AddPrimitive("JCMROOT", dp.StringPrimitive(True, JCMROOT))
    datatree.AddPrimitive("Login", dp.StringPrimitive(True, Login))
    if (SSHClient is not None): 
        datatree.AddPrimitive("SSHClient", dp.StringPrimitive(True, SSHClient))
    if (SSHAgentForwarding is not None):
        datatree.AddPrimitive("SSHAgentForwarding", dp.StringPrimitive(False, 'yes' if (SSHAgentForwarding) else 'no'))
    if (SSHTimeOut is not None):
        datatree.AddPrimitive("SSHTimeOut", dp.NumberPrimitive(SSHTimeOut, int))
    datatree.AddPrimitive("Multiplicity", dp.NumberPrimitive(Multiplicity, int))
    
    queue = db.TreeDir.Create('Queue')
    queue.AddPrimitive("Type", dp.StringPrimitive(True, Type))
    queue.AddPrimitive("JobName", dp.StringPrimitive(True, JobName))
    queue.AddPrimitive("PartitionName", dp.StringPrimitive(True, PartitionName))
    if not NNodes is None:
        queue.AddPrimitive("NNodes",  dp.NumberPrimitive(NNodes, int))
    if not NTasks is None:
        queue.AddPrimitive("NTasks",  dp.NumberPrimitive(NTasks, int))
    if not NTasksPerNode is None:
        queue.AddPrimitive("NTasksPerNode",  dp.NumberPrimitive(NTasksPerNode, int))
    exclude = True
    if not NodeList == '':
        queue.AddPrimitive("NodeList", dp.StringPrimitive(True, NodeList))
    else: exclude = False
    if not ExcludeNode == '' or not exclude:
        queue.AddPrimitive("ExcludeNode", dp.StringPrimitive(True, ExcludeNode))
    queue.AddPrimitive("WorkingDir", dp.StringPrimitive(True, WorkingDir))
    queue.AddPrimitive("NThreads", dp.NumberPrimitive(NThreads, int))
    if Time is not None:
        queue.AddPrimitive("Time", dp.NumberPrimitive(Time, float))
    if MemoryPerJob is not None:
        queue.AddPrimitive("MemoryPerJob", dp.NumberPrimitive(MemoryPerJob, float))
    if (Exclusive is not None):
        datatree.AddPrimitive("Exclusive", dp.StringPrimitive(False, 'yes' if (Exclusive) else 'no'))
    if Features is not None:
        queue.AddPrimitive("Features", dp.StringPrimitive(True, Features))
        
    if not OOCDir is None:
      queue.AddPrimitive("OOCDir", dp.StringPrimitive(True, OOCDir))
    if not MaxCoreSize is None:
      queue.AddPrimitive("MaxCoreSize", dp.NumberPrimitive(MaxCoreSize, int))

    if Environment is not None:
        queue.AddPrimitive("Environment", dp.StringPrimitive(True, Environment))
      
    datatree.AddTreeDir(queue)

    daemonAnswer = run_command(datatree)
    return extractReturnValue(daemonAnswer)
    

def job_info(job_ids = None, status_only=False):
    """
    Returns all the available information for the given job_ids (all job_ids
    are used as default).
    """
    if job_ids is None:
        job_ids = []
    if isinstance(job_ids,int):
        job_ids = [job_ids]
    datatree = db.TreeDir.Create('JobInfo')
    datatree.AddPrimitive("Id", dp.VectorPrimitive(job_ids,int))
    datatree.AddPrimitive("StatusOnly", 
                                dp.NumberPrimitive(int(status_only), int))
    daemonAnswer = run_command(datatree)
    value = extractReturnValue(daemonAnswer)
    return value
 
 
def resource_info(ids = None):
    """
    Returns the resource information for a given resource id.
    """
    if ids is None:
        ids = []
    datatree = db.TreeDir.Create('ResourceInfo')
    datatree.AddPrimitive("Id", dp.VectorPrimitive(ids,int))
    daemonAnswer = run_command(datatree)
    
    value = extractReturnValue(daemonAnswer)
    pprint.pprint(value, width=80)
    return value
    
    
def release(resource_id = None, Hostname=''):
    """
    Removes a resource from the daemon.
    """
    if resource_id is None:
        resource_id = []
    datatree = db.TreeDir.Create('RemoveResource')
    datatree.AddPrimitive("Hostname", dp.StringPrimitive(True, Hostname))
    datatree.AddPrimitive("Id", dp.VectorPrimitive(resource_id,int))
    daemonAnswer = run_command(datatree)
    print(extractReturnValue(daemonAnswer))


def kill(job_ids = None):
    """
    Closes a running job with given id.
    """
    if isinstance(job_ids,int):
        job_ids = [job_ids]

    killAll=False
    if job_ids is None:
        job_ids = []
        killAll=True

    datatree = db.TreeDir.Create('CloseJob')
    datatree.AddPrimitive("Id", dp.VectorPrimitive(job_ids,int))
    daemonAnswer = run_command(datatree)

    if killAll: 
        job_ids.extend(__private.JCMdaemon.temporaryIDs)
        job_ids.extend(__private.JCMdaemon.cachedIDs)

    for job_id in job_ids:
        if job_id in __private.JCMdaemon.temporaryIDs:
            __private.JCMdaemon.temporaryIDs.remove(job_id)
        if job_id in __private.JCMdaemon.cachedIDs:
            del __private.JCMdaemon.cachedIDs[job_id]
        backtraceID = 'job_{0}'.format(job_id)
        if not hasattr(__private.JCMdaemon, backtraceID): continue
        backtrace = getattr(__private.JCMdaemon, backtraceID)
        # remove the backtrace iD instance from the class
        delattr(__private.JCMdaemon, backtraceID)
        for jcm_file in backtrace.produced_jcm_files:
            del __private.jcmt2jcm[jcm_file]
        if not backtrace.clean_up: continue
        shutil.rmtree(backtrace.working_dir_base, ignore_errors=True)
        try: os.rmdir(os.path.dirname(backtrace.working_dir_base))
        except: pass    

    if killAll:  
        attr=dir(__private.JCMdaemon)
        for iA in attr:
            if not iA.startswith('job_'): continue;
            backtrace = getattr(__private.JCMdaemon, backtraceID)
            # remove the backtrace iD instance from the class
            delattr(__private.JCMdaemon, backtraceID)
            for jcm_file in backtrace.produced_jcm_files:
                print(jcm_file)
                del __private.jcmt2jcm[jcm_file]
            if not backtrace.clean_up: continue
            shutil.rmtree(backtrace.working_dir_base, ignore_errors=True)
            try: os.rmdir(os.path.dirname(backtrace.working_dir_base))
            except: pass    

#     print extractReturnValue(daemonAnswer)


def shutdown():
    """
    Completely shuts down the daemon.
    """
    if not daemonCheck(warn=False): 
        return
    datatree = db.TreeDir.Create('Shutdown')
    run_command(datatree, False)

    attr=dir(__private.JCMdaemon)
    for iA in attr:
        if not iA.startswith('job_'): continue;
        backtrace = getattr(__private.JCMdaemon, iA)
        for jcm_file in backtrace.produced_jcm_files:
            del __private.jcmt2jcm[jcm_file]
        if not backtrace.clean_up: continue
        shutil.rmtree(backtrace.working_dir_base, ignore_errors=True)
        try: os.rmdir(os.path.dirname(backtrace.working_dir_base))
        except: pass    
        

    del __private.JCMdaemon


def submit_job(project=list(),
               mode='solve',
               resources = None,
               logFile= None):
    """
    Submits a job using a project file with a specific mode.
    """
    if resources is None:
        resources = []
    datatree = db.TreeDir.Create('SubmitJob')
    if not isinstance(project, list): project=[project]
    for i_project in project:
      datatree.AddPrimitive("ProjectFile", dp.StringPrimitive(True, i_project))
    datatree.AddPrimitive("Mode", dp.StringPrimitive(True, mode))
    datatree.AddPrimitive("Resource", dp.VectorPrimitive(resources,int))
    if logFile is not None:
        datatree.AddPrimitive("LogFile", dp.StringPrimitive(True, logFile))
    daemonAnswer = run_command(datatree)
    return extractReturnValue(daemonAnswer)


def wait(job_ids=None, 
         resultbag=None,
         verbose=True, 
         timeout=1e15, 
         break_condition='all'):
    """
    Function that waits for the jobs with the given job_ids to finish (default:
    all jobs) and returns a list of all results and logs. Example::

        job_ids = []
        ...
        job_id = jcmwave.solve('project.jcmp',keys)
        job_ids.append(job_id)
        results, logs = jcmwave.daemon.wait(job_ids)

    :param list job_ids: integer vector of job identifier as returned by jcmwave_solve
        If missing or empty all job ids available on the daemon are used.
        A zero job id is treated as a dummy.    

    :param Resultbag resultbag: An instance of the class :class:`jcmwave.Resultbag`. 
        The result is added to the result bag. If the corresponding 
        :func:`jcmwave.solve` command was not called with the resultbag 
        parameter an error will be thrown.        

    :param bool verbose: Show progress reporting. (default:True)

    :param int timeout: Time out in seconds (optional).This script returns with 
        empty ouput values, when the time out is reached. 
        
    :param str break_condition: If set to 'any' ('all') the function waits until 
        one job (all jobs) from a list of jobs has finished. (default: 'all')

    :returns: A tuple (results, logs) 

        :results: List containing the computed results for each job
            as referenced by the job_ids vector.
        :logs: List containing the corresponding log messages of the jobs.  
    
        If a resultbag is passed the output is stored in the resultbag and
        is not returned.    
        
    """
    
    if job_ids is None:
        job_ids = []
    elif isinstance(job_ids,int):
        job_ids = [job_ids]

    # Check if there is a running daemon and a socket
    if not daemonCheck():
        return
    
    # Type-checking
    if not isinstance(break_condition, str) and (
                not break_condition in ['all', 'any', 'cache']):
        raise TypeError('break_condition -> "all" or "any" expected.') # cache is only used internally
    
    # Get a list of all running jobs from the daemon, if no explicit list of
    # job_ids was given
    if job_ids == []:
        stat = status()
        jobs = stat['Jobs']
        for j in jobs:
            IDs = jobs[j]
            for id in IDs:
                if not id in job_ids:
                    job_ids.append(id)

    job_ids = [id for id in job_ids if id > 0] # this is different from matlab interface:
                                              # empty results for zero job ids are not returned
    job_id_to_return_index = dict() # same as job id to index in job_ids vector
    for i, iD in enumerate(job_ids):
        job_id_to_return_index[iD]=i;
    job_ids=set(job_ids)
    
    # define the initial wait interval
    min_wait_interval = 0.1;
    max_wait_interval = 2;
    if not timeout == 1e15:
      min_wait_interval = timeout / 100
      max_wait_interval = timeout / 10
    wait_interval = min_wait_interval
    
    # Initializations
    t0 = time.time()

    running_job_ids = set.difference(job_ids, __private.JCMdaemon.cachedIDs)
    if (break_condition == 'any') and (len(running_job_ids)<len(job_ids)):
        running_job_ids.clear()
    
    # Loop that runs till all jobs are finished and adjusts the wait time in
    # each loop
    while (len(running_job_ids)>0):
        job_info_= job_info(list(running_job_ids), True)
        job_status = job_info_['Status']
        if (break_condition != 'cache') and (('Warning' in job_info_) and job_info_['Warning']=='No resources'):
            raise Exception('No computer resources available while waiting.')
            return
        if not isinstance(job_status, list): job_status=[job_status] 
        finished_job_ids = [iD for iD, iStatus in zip(running_job_ids, job_status) if iStatus=='Finished']
        if (break_condition == 'any') and (len(finished_job_ids)>0):
            finished_job_ids = [finished_job_ids[0]]
        parse_time = 0.0;
        if len(finished_job_ids)>0:
            parse_time=time.time();
            job_infos = job_info(finished_job_ids)['Job']

            # gather first all results to be more resilient in case of an interrupt
            # (i.e. user Control-C)
            results=[None]*len(finished_job_ids)
            logs=[None]*len(finished_job_ids)
            infos=[None]*len(finished_job_ids)
            keys=[None]*len(finished_job_ids)
            for iF, iD in enumerate(finished_job_ids):
                backtraceID = 'job_{0}'.format(iD)
                try: backtrace = getattr(__private.JCMdaemon, backtraceID)
                except AttributeError: 
                    running_job_ids.remove(iD)
                    continue                
                if not isinstance(job_infos, list): job_infos = [job_infos]
                j_info = job_infos[iF]
                if (j_info['ExitCode'] == 0):
                    if j_info['Log']['Out'] == 'Project is up-to-date.':
                        stat = 'Up-to-date'
                    else: stat = 'Finished'
                else: stat = 'Failed'

                thisInfo='{0}: {1}'.format(stat, ', '.join(backtrace.files))
                if verbose:
                    print(thisInfo)
                    thisInfo=''
        
                thisLog = {}
                thisLog['ExitCode'] = j_info['ExitCode']
                thisLog['Log'] = j_info['Log']

                if thisLog['ExitCode'] == 0:
                    thisResults=list()
                    for i_project in range(0, len(backtrace.files)):
                        thisResults.append(gather_results(
                            backtrace.files[i_project], backtrace.eigdate_old[i_project], backtrace.mode, 
                            backtrace.table_format, backtrace.cartesianfields_format))
                    if not backtrace.isProjectSequence: thisResults=thisResults[0]
                else:
                    thisResults = []

                key=None;
                if (resultbag is not None): 
                  resultbag.add(id = iD, result = thisResults, log = thisLog)
                  key=resultbag.get_keys_by_job_id(iD)
                  resultbag.release(iD)
                  
                  thisResults=None
                  thisLog=None
                  
                results[iF]=thisResults
                logs[iF]=thisLog
                infos[iF]=thisInfo
                keys[iF]=key
                
                del thisResults
                del thisLog
                running_job_ids.remove(iD)
                __private.JCMdaemon.cachedIDs[iD]=[results[iF], logs[iF], infos[iF], keys[iF]]

            del results
            del logs


            
            # clear backtrace entries
            for iF, iD in enumerate(finished_job_ids):        
                backtraceID = 'job_{0}'.format(iD)
                try: backtrace = getattr(__private.JCMdaemon, backtraceID)
                except: continue                

                # remove the backtrace iD instance from the class
                delattr(__private.JCMdaemon, backtraceID)

                for jcm_file in backtrace.produced_jcm_files:
                    del __private.jcmt2jcm[jcm_file]
        
                if backtrace.clean_up:
                    shutil.rmtree(backtrace.working_dir_base)
                    try: os.rmdir(os.path.dirname(backtrace.working_dir_base))
                    except: pass
                if iD in __private.JCMdaemon.temporaryIDs:
                   __private.JCMdaemon.temporaryIDs.remove(iD) 

            parse_time=time.time()-parse_time;
            
        # break conditions
        if break_condition == 'cache': break
        if break_condition == 'any' and finished_job_ids != []: break
        if (time.time() - t0) >= timeout:
            return None, None, None
            break 
        
        # adjust wait time interval
        if (len(finished_job_ids)==0):
            wait_interval = min([wait_interval * 2, max_wait_interval]) 
        else:
            wait_interval = max([wait_interval / 2, min_wait_interval])

        sleep_time=wait_interval-parse_time; 
        if not timeout == 1e15:
            sleeptime=min(sleep_time, timeout-((time.time() - t0)+sleep_time))
        time.sleep(max(0, sleep_time))
        
    if  break_condition == 'cache':   
        return set.difference(job_ids,  __private.JCMdaemon.cachedIDs)
    #return_index = 0
    results = [None] * len(job_ids)
    logs = [None] * len(job_ids)

    job_ids = set.intersection(job_ids, __private.JCMdaemon.cachedIDs)

    # release job from daemon
    datatree = db.TreeDir.Create('CloseJob')
    datatree.AddPrimitive("Id", dp.VectorPrimitive(
        list(job_ids), int))
    daemonAnswer = run_command(datatree)
    
    finished_ids = []
    for iD in job_ids:
        return_index = job_id_to_return_index[iD]
        finished_ids.append(return_index)
        thisResults = __private.JCMdaemon.cachedIDs[iD][0]
        thisLog = __private.JCMdaemon.cachedIDs[iD][1]
        thisInfo =  __private.JCMdaemon.cachedIDs[iD][2]
        thisKey =  __private.JCMdaemon.cachedIDs[iD][3]
        del __private.JCMdaemon.cachedIDs[iD]

        if verbose and len(thisInfo)>0:
            print(thisInfo);
        
        if (resultbag is not None):
            if (thisResults is not None): 
                resultbag.add(id = iD, result = thisResults, log = thisLog)
                resultbag.release(iD)
            elif thisKey is not None:
                try :
                    thisResults=resultbag.get_result(thisKey)
                except: 
                    thisResults=[]
                thisLog=resultbag.get_log(thisKey)
                    
        results[return_index] = thisResults 
        logs[return_index] = thisLog
    
    if break_condition == 'any':
        return finished_ids, results, logs
    else:
        return results, logs


def gather_results(project_file, eigdate_old, mode, table_format, 
                     cartesianfields_format):
    """
    Function used by wait() to collect all produced results.
    """

    results=[]
    project_dir = os.path.split(os.path.abspath(project_file))
    
    try:
        with open(project_file, 'r') as f: jcm = f.read()
        # skip comments
        jcm = re.sub('#.*', '', jcm)
        jcm = re.sub('\r\n', ' \n',jcm)
        
        reStr = '(Project)|(Problem)[\n ]*[=]?[\n ]*{'
        if mode =='solve' and not (re.findall(reStr ,jcm ) == None):
            
            #result_dir = re.sub('.jcmp', '_results', project_file)
            result_dir = project_file.replace('.jcmp', '_results')
            fieldbagFile =  os.path.join(result_dir, 'fieldbag.jcm')
            
            solveResults = dict()
            if sys.platform == "linux2":
                st=os.stat(os.path.dirname(fieldbagFile))
                os.chown(os.path.dirname(fieldbagFile), st.st_uid, -1)
            if os.path.isfile(fieldbagFile):
                solveResults['file'] = fieldbagFile
            try: solveResults['computational_costs'] = jcmwave.loadtable(
                os.path.join(result_dir, 'computational_costs.jcm')) 
            except: pass
            try:
                if 'ResonanceMode' in jcm or 'PropagatingMode' in jcm: 
                    solveResults['eigenvalues'] = jcmwave.loadtable(
                        os.path.join(result_dir, 'eigenvalues.jcm'))
            except: pass 
            results.append(solveResults)
                
        outs = re.findall('OutputFileName[\n ]*=[\n ]*"([^"]*)"', jcm)
        for out in outs:
            resultFile = os.path.abspath(os.path.join(project_dir[0], out))
            
            if sys.platform == "linux2":
                st=os.stat(os.path.dirname(resultFile))
                os.chown(os.path.dirname(resultFile), st.st_uid, -1)
            count = 0
            while (not os.path.isfile(resultFile)) and (count<30):
                time.sleep(1)
                count += 1
            if not count == 0:
                print('Waited {0} seconds for the file system...'.format(count))
                print('The problem occurred with file:', resultFile)
            results.append(resultFile)
            
            accepted=False
            try:
                results[-1] = jcmwave.loadtable(results[-1], table_format)
                accepted=True
            except:
                pass

            if not accepted and not cartesianfields_format == 'filepath':
                try:
                    results[-1] = jcmwave.loadcartesianfields(
                                        results[-1], cartesianfields_format)
                    accepted=True
                except:
                    pass
        return results
    except:
        results = []
        fp.close()





