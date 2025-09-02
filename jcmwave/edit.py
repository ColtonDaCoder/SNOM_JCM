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
# Primary author: Philipp Schneider
#                 (based on MATLAB-version by Lin Zschiedrich)
# Date:           03/08/2017
#
# ==============================================================================


# Imports
# ------------------------------------------------------------------------------
import jcmwave
import jcmwave.__private as __private
import os

# Name space helper class
# ------------------------------------------------------------------------------
class NameSpaceHelper(object):
    pass

# Function definitions
# ------------------------------------------------------------------------------

def edit(file_name=None, line=1, col=1, set_status=None, hint=''):
    """
    Starts JCMcontrol in the editor mode. 
   
    :param str file_name: Path to a JCMwave file.
        
    :param int line: Jumps to the line number within the file.

    :param int col: Jumps to the column number within the file.
        
    :param str set_status:  (None|"on"|"off")
        When using :func:`jcmwave.geo` or :func:`jcmwave.solve` the JCMwave editor pops up automatically, if an error was detected in one of the  JCMwave input files (not in daemon mode). 
        With set_status this behaviour can be switched on or off.
 
    :param str hint: Show hint string in the editor.
 
    """       
    
    #initialize JCMedit
    if not hasattr(__private, 'JCMedit'):
        try:
            __private.JCMedit = NameSpaceHelper()
            _startJCMedit()
            __private.JCMedit.off = False
        except Exception as e:
            __private.warning('Could not start JCMedit. %s' % str(e))
            return
        
    # Set default message
    message = '__popup__';        
        
    # Handle opening of file
    if file_name is not None:
        if not os.path.isfile(file_name):
            raise EnvironmentError('Cannot access file %s.' % (file_name))

        line = int(line)
        col = int(col)
        
        if line < 1:
            raise ValueError('Invalid parameter for line: %s.' % (line))
        if col < 1:
            raise ValueError('Invalid parameter for col: %s.' % (col))
            
        message = '%s!;!%d!;!%d!;!%s' % (file_name, line, col, hint)

    # Change status
    if set_status is not None:
        if set_status not in ['on','off']:
            raise ValueError('set_status must be either "on" or "off".')
        __private.JCMedit.off = (set_status == 'off')
        if set_status == 'off': message = 'shutdown'
        
    # Editor Interaction
    if not __private.JCMedit.off or message == 'shutdown':
        socket = __private.JCMedit.python_socket
        try:
            __private.send_message(socket, message, get_answer = False)  
        except:
            # Maybe editor was closed by user. Open it again
            try:
                _startJCMedit()
                socket = __private.JCMedit.python_socket
                __private.send_message(socket, message, get_answer = False)  
            except:
                __private.warning('Could not start JCMedit.')
                return    

    # Show warning if Editor was switched off
    if __private.JCMedit.off and message != 'shutdown':
        __private.warning('JCMedit was switched off. '+
            'Use jcmwave.edit(set_status="on") to switch it on again.'
                )
    
def _startJCMedit():

    # Check if all JCMwave binary locations are known...
    if not 'JCMsolve' in dir(__private):
        jcmwave.startup() # ...load them if not
    elif __private.JCMsolve == None:
        jcmwave.startup()

    try:
        pid = os.getppid()
    except:
        pid = 0 #on windows systems, there is no getppid

    __private.JCMedit.python_socket,_,_ =  __private.run_command(
        JCMsolve=__private.JCMsolve, 
        command='--start_edit',
        calling_pid=pid
    )
        


# Test functionality
# ------------------------------------------------------------------------------
if __name__=='__main__':
    from builtins import input

    filePath = 'test.txt'
    with open(filePath,'w') as f:
        f.write("Lorem ipsum\nTest test test\nLorem ipsum\nTest test test\n")

    input('Press "Enter" to open file.')
    edit(filePath,2,4)

    input('Press "Enter" popup editor.')
    edit()
    
    input('Press "Enter" to show hint.')
    edit(filePath,3,1, 'Some hint')

    input('Press "Enter" to close file and set status to "off".')
    edit(set_status='off')

    input('Press "Enter". Editor should not open.')
    edit(filePath,2,4)

    input('Press "Enter" set status to "on" and to open file again')
    #switch on
    edit(set_status='on')        
    #Show file again
    edit(filePath,2,4,'another hint')

    input('Press "Enter" to close file and set status to "off".')
    edit(set_status='off')

    input('Press "Enter" to exit and remove test file.')
    os.remove('test.txt')
    
    
