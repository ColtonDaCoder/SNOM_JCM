import sys, os
import notebook.notebookapp as app
import platform
import ctypes
import time
import logging
from multiprocessing import Process
import sys
import signal
import runpy


#Check if pid is running
def is_pid_running(pid):
    return (_is_pid_running_on_windows(pid) if platform.system() == "Windows"
        else _is_pid_running_on_unix(pid))
 
def _is_pid_running_on_unix(pid):
    try: os.kill(pid, 0)
    except OSError: return False
    return True
 
def _is_pid_running_on_windows(pid):
    import ctypes.wintypes
    
    Psapi = ctypes.WinDLL('Psapi.dll')
    EnumProcesses = Psapi.EnumProcesses
    EnumProcesses.restype = ctypes.wintypes.BOOL
    
    count = 64
    while True:
        ProcessIds = (ctypes.wintypes.DWORD*count)()
        cb = ctypes.sizeof(ProcessIds)
        BytesReturned = ctypes.wintypes.DWORD()
        if EnumProcesses(ctypes.byref(ProcessIds), cb, ctypes.byref(BytesReturned)):
            if pid in ProcessIds: return True
            if BytesReturned.value<cb:
                break
            else:
                count *= 2
        else:
            raise EnvironmentError("Call to EnumProcesses failed")

    return pid in ProcessIds

if __name__=='__main__':
  #Get calling pid and delete from command line arguments
  calling_pid = int(sys.argv[1])
  del sys.argv[1]

  ch = logging.StreamHandler()
  logger = logging.getLogger('NotebookApp')
  logger.addHandler(ch)

  #If required, output errors to additional log file:
  #fh = logging.FileHandler("/tmp/out.log")
  #logger.addHandler(fh)
  
  #Start jupyter server with remaining command line arguments
  t = Process(target=app.main,args=())
  t.daemon = True
  t.start()
  t.kill = False

  #Deal with kill signal
  def sigint_handler(signal, frame): sys.exit(0)
  signal.signal(signal.SIGINT, sigint_handler)
  signal.signal(signal.SIGTERM, sigint_handler)


  #run loop while pid is running
  while True:
      if not is_pid_running(calling_pid) or t.kill: break
      time.sleep(5)
