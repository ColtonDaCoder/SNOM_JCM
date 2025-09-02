# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 3237 $


from __future__ import print_function
import subprocess
import os
import sys
from subprocess import Popen
from subprocess import PIPE
import threading 

class BackgroundCommand(threading.Thread):
    def __init__(self, process, exe):
       self.process = process
       self.exe = exe;
       self.stderr=None
       self.stdout=None
       threading.Thread.__init__(self)
    def run(self):
       (self.stdout, self.stderr) =  self.process.communicate()
       if (self.stderr is not None) and (len(self.stderr)>0):
          print("Background process %s aborted: %s" % (self.exe, self.stderr));

        


def call_tool(exe, args, stdout=None, stderr=None, background=False):

  if stdout is None: stdout=PIPE
  if stderr is None: stderr=PIPE

  print_out = False
  if stdout == sys.stdout:
      stdout=PIPE #sys.stdout fails on windows os and on ipython consoles
      print_out = True

  close_fds = os.name!='nt'
   
  p = Popen(('"%s"' %(exe,))+' '+args, shell=True,
            stdin=PIPE, stdout=stdout, stderr=stderr, 
            close_fds=close_fds);

  if not background:
      if print_out:
          for line in p.stdout: print(line.decode(),end='')
      (stdoutdata, stderrdata) = p.communicate()
      if not stdoutdata is None: stdoutdata=stdoutdata.decode()
      if not stderrdata is None: stderrdata=stderrdata.decode()
  else: 
    bkg = BackgroundCommand(p, exe);
    bkg.setDaemon(True);
    bkg.start();
    return

  return stdoutdata, stderrdata, p.returncode
