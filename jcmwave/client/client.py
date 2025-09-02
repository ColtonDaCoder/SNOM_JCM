from .requestor import Requestor
from .study import Study
from .benchmark import Benchmark
import time
import json

class Client(Requestor):

    '''
    This class provides methods for creating new optimization studies. Example::

        domain = [
          {'name': 'x1', 'type': 'continuous', 'domain': (-1.5,1.5)}, 
          {'name': 'x2', 'type': 'continuous', 'domain': (-1.5,1.5)},
       ]
       study = client.create_study(domain=domain, name='example')

    '''
    
    def __init__(self, host, verbose=True, check=True):
        super(Client, self).__init__(host=host,verbose=verbose)
        if check: self.check_server()

    def _get_driver_doc(self, driver_name, doc_type, save_dir, language):
        #Create a test file for a specific driver and save it to save_dir
        answer = self.post('server', 'get_driver_doc', data = {
            'driver_name': driver_name,
            'doc_type': doc_type,
            'save_dir': save_dir,
            'language': language,
        })
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not create test file. Error: '
                                   + answer['error'])
        return answer
    
    def check_server(self):
        """ Checks if the optimization server is running. 
        Example:
 
            >>> client.check_server()
            Optimization server is running

        """
        print('Polling server at {}'.format(self.host))
        answer = self.get()
        print(answer['message'])

        
    def shutdown_server(self, force=False):
        """Shuts down the optimization server. Example::

            client.shutdown_server()

         :param bool force: If True the optimization server is closed even if a study
             is not yet finished.

        """
        force= 1 if force else 0
        answer = self.post('server', 'shutdown', data = {'force': force})
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not shut down server. Error: '
                                   + answer['error'])
        print('Server at {} is shutting down.'.format(self.host))
        
    def create_study(self, domain=None, name=None, study_id=None, constraints=None,
                     driver='BayesOptimization', save_dir=None,
                     output_precision=1e-10,
                     dashboard=True,open_browser=True):
        """Creates a new :class:`~client.Study` instance. Example::

            study = client.create_study(domain=domain, name='example')

        :param list domain: List of domain definitions for each parameter. A domain 
            definition consists of a dictionary with the entries

            :name: Name of the parameter. E.g. 'x1'. The name should contain
                no spaces and must not be equal to function names like 
                'sin', 'cos', 'exp' etc.
            :type: Type of the parameter. Either 'continuous', 'discrete', 
                'categorial', or 'fixed'. Fixed parameters are not optimized, 
                but can be used in the constraint functions.
            :domain: The domain of the parameter. For continuous parameters this
                is a tuple (min, max). For discrete parameters this is a list
                of values, e.g. [1.0,2.5,3.0]. For categorial inputs it is a list
                of strings, e.g. ['cat1','cat2','cat3']. Note, that categorial
                values are internally mapped to integer representations, which
                are allowed to have a correlation. The categorial values should 
                therefore be ordered according to their similarity. 
                For fixed parameters the domain is a single parameter value.

            Example::

                domain = [{'name': 'x1', 'type': 'continuous', 'domain': (-2.0,2.0)}, 
                          {'name': 'x2', 'type': 'continuous', 'domain': (-2.0,2.0)},
                          {'name': 'x3', 'type': 'discrete', 'domain': [-1.0,0.0,1.0]},
                          {'name': 'x4', 'type': 'categorial', 'domain': ['a','b']}
                          {'name': 'x5', 'type': 'fixed', 'domain': 2.0}]
   
            
        :param list constraints: List of constraints on the domain. Each list element is a
            dictionary with the entries

            :name: Name of the constraint.
            :constraint: A string defining a function that is smaller zero if and 
                only if the constraint is met. The following operations and 
                functions may be used: +,-,*,/,^,sqrt,sin,cos,tan,abs,round,
                sgn, tunc. E.g. ``'x1^2 + x2^2 + sin(x1+x2)'``

            Example::

                constraints = [
                    {'name': 'circle', 'constraint': 'x1^2+x2^2-4'},
                    {'name': 'triangle', 'constraint': 'x1-x2'},
                ]

        :param str study_id: A unique identifier of the study. All relevant information on 
            the study are saved in a file named study_id+'.jcmo'
            If the study already exists, the ``domain`` and ``constraints``
            do not need to be provided. If not set, the study_id is set to
            a random unique string.

        :param str name: The name of the study that will be shown in the dashboard.

        :param str save_dir: The path to a directory, where the study file (jcmo-file) 
            is saved. If False, no study file is saved.

        :param str driver: Driver used for the study (default: 'BayesOptimization').
            For a list of drivers, see the `Analysis and Optimization 
            Toolkit/Driver Reference 
            </JCMsuite/html/PythonInterface/4a227264035a2012db36e44865006686.html>`_.

        :param float output_precision: Precision level for ouput of parameters. 
            (Default: 1e-10)

            .. note:: Rounding the output can potentially lead to a slight 
               breaking of constraints.

        :param bool dashboard: If true, a dashboard server will be started for the study.
            (Default: True)

        :param bool open_browser: If true, a browser window with the dashboard is started.
            (Default: True)
        
        """
        
        answer = self.post('study', 'create', data = {
            'study_id': study_id,
            'name': name,
            'domain': json.dumps(domain),
            'constraints': json.dumps(constraints),
            'driver': driver,
            'save_dir': save_dir,
            'output_precision': output_precision,
            'dashboard': dashboard,
            'open_browser': open_browser
        })
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not create study. Error: '
                                   + answer['error'])
        
        study = Study(study_id = answer['study_id'],
                      host=self.host, session=self.session)

        if answer['dashboard_path']:
            print('The dashboard is accessible via {}/{}'.format(
                self.host,answer['dashboard_path']))
        return study

    def create_benchmark(self, benchmark_id=None, num_average=None):
        """Creates a new :class:`~client.Benchmark` object for benchmarking 
        different optimization studies against each other. Example::

            benchmark = client.create_benchmark(num_average=6);

        :param str benchmark_id: A unique identifier of the benchmark.
        :param int num_average: Number of study runs to determine average 
            study performance        
        """
        
        answer = self.post('benchmark', 'create', data = {
            'benchmark_id': benchmark_id,
            'num_average': num_average
        })
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not create benchmark. Error: '
                                   + answer['error'])
        
        benchmark = Benchmark(benchmark_id = answer['benchmark_id'],
                        num_average=num_average,
                        host=self.host, session=self.session)
        return benchmark
