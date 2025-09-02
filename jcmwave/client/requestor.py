import threading
template = ('Please install the package {p} (e.g. run "pip install {p}") ' +
        'or use the python binary provided in "ThirdPartySupport/Python/bin".')
try: import requests
except ImportError: raise ImportError(template.format(p='requests'))
try: import json
except ImportError: raise ImportError(template.format(p='json'))
try: import colorama
except ImportError: raise ImportError(template.format(p='colorama'))
try: from datetime import datetime as dt
except ImportError: raise ImportError(template.format(p='datetime'))

class Requestor(object):

    def __init__(self, host, session=None, verbose=True):

        is_in_notebook = False        
        try:
            shell = get_ipython().__class__.__name__
            is_in_notebook = (shell == 'ZMQInteractiveShell')
        except: pass
        if not is_in_notebook: colorama.init()
        
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session
        self.verbose = verbose
        self.lock = threading.Lock()
        self.host = host
        
    def print_messages(self,answer):
        if not self.verbose: return
        status_code = answer['status_code']
        if status_code >= 200 and status_code < 300:
            messages = json.loads(answer['messages'])
            for idx in sorted(messages['message']):
                message_str = messages['message'][idx]
                message_type = messages['type'][idx]
                message_time = messages['datetime'][idx]
                self.print_message(message_str,message_time,message_type)

    def print_message(self,message_str,message_time=None,message_type='remark',
                      style='normal'):
        if message_time is None: message_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        DATE = colorama.Fore.GREEN+colorama.Style.DIM
        RESET = colorama.Style.RESET_ALL
        if message_type == 'danger': STYLE = colorama.Fore.RED
        elif message_type == 'warning': STYLE = colorama.Fore.YELLOW
        elif message_type == 'remark': STYLE = colorama.Fore.CYAN
        else: STYLE = ''
        if style == 'heading': STYLE += colorama.Style.BRIGHT
        print(DATE+message_time+': '+RESET+STYLE+message_str+RESET)
    
    def get(self,object=None,id=None,type=None):
        url = self.host
        if object is not None: url += '/'+object
        if id is not None: url += '/'+id
        if type is not None: url += '/'+type
        try:
            with self.lock:
                r = self.session.get(url)
        except requests.exceptions.ConnectionError as e:
            raise EnvironmentError('Could not connect to server. '+
                'Please check if the optimization server is running on {}.'.format(
                    self.host))
                
        try:answer = r.json()
        except Exception as e:
            raise EnvironmentError(
                'Cannot decode answer: {} \n {}'.format(str(e),r._content))
        return answer
        
    def post(self,object,operation,id=None,data=None):
        #make dummy data to ensure this is interpreted as post request by server
        if data is None: data = {'0':0} 
        url = self.host+'/'+object +'/'+operation
        if id is not None: url += '/'+id
        try:
            with self.lock:
                r = self.session.post(url, data)

        except requests.exceptions.ConnectionError as e:
            raise EnvironmentError('Could not connect to server. '+
                'Please check if the optimization server is running on {}.'.format(
                    self.host))
                    
        try:answer = r.json()
        except Exception as e:
            raise EnvironmentError(
                'Cannot decode answer: {} \n {}'.format(str(e),r._content))
        
        self.print_messages(answer)
        return answer
