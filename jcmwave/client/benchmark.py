from .requestor import Requestor
import time
import datetime as dt
import json
import warnings

class Benchmark(Requestor):
    
    '''
    This class provides methods for benchmarking different optimization studies
    against each other. Example::
   
       benchmark = Benchmark(num_average=6)
       benchmark.add_study(study1)
       benchmark.add_study(study2)
       benchmark.set_objective(objective)
       benchmark.run()
       data = benchmark.get_data(x_type='num_evaluations',y_type='objective',
                  average_type='mean')
       fig = plt.figure(figsize=(8,4))
       for idx,name in enumerate(data['names']):
           X = data['X'][idx]
           Y = np.array(data['Y'][idx])
           std_error = np.array(data['sdev'][idx])/np.sqrt(6)
           p = plt.plot(X,Y,linewidth=2.0, label=name)
           plt.fill_between(X, Y-std_error, Y+std_error, alpha=0.2, color = p[0].get_color())
       plt.legend(loc='upper right',ncol=1)
       plt.grid()
       plt.ylim([0.1,10])
       plt.rc('font',family='serif')
       plt.xlabel('number of iterations',fontsize=12)
       plt.ylabel('average objective',fontsize=12)
       plt.show()
    '''

    def __init__(self, host, benchmark_id, session, num_average):
        super(Benchmark, self).__init__(host=host,session=session)
        self.id = benchmark_id
        self.num_average = num_average
        self._studies = []
    
    def __del__(self):
        answer = self._post('benchmark', 'delete')
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not delete benchmark. Error: '
                                   + answer['error'])
        
    def _post(self,object,operation,data={}):
        return super(Benchmark, self).post(object,operation,self.id,data)

    def _get(self,object,type):
        return super(Benchmark, self).get(object,self.id,type)


    def add_study(self, study):
        ''' Adds a study to the benchmark. Example::
        
                benchmark.add_study(study1)

        :param study: A ``Study()`` object.
        '''
        answer = self._post('benchmark', 'add_study', data={'study_id': study.id})
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not add study to benchmark. Error: '
                                   + answer['error'])
        self._studies.append(study)

    @property  
    def studies(self):
        ''' A list of studies to be run for the benchmark.'''
        studies = []
        for s in self._studies:
            for num_run in range(self.num_average):
                studies.append(s)
        return studies

    def add_study_results(self, study):
        ''' Adds the results of a benchmark study at the end of an optimization run. 
        Example::
        
            benchmark.add_study_results(study1)

        :param study: A ``Study()`` object after the study was run.
        '''
        answer = self._post('benchmark', 'add_study_results',
                                data={'study_id': study.id})
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not add study results to benchmark. Error: '
                                   + answer['error'])


    def get_data(self, **kwargs):
        ''' Get benchmark data. Example::
        
            data = benchmark.get_data( x_type='num_evaluations', y_type='objective',
                 average_type='mean')
            plt.plot(data['X'][0],data['Y'][0])

        :param str x_type: Data on x-axis. Can be either 'num_evaluations' or 'time'
        :param str y_type: Data type on y-axis. Can be either 'objective', 'distance', 
            (i.e. accumulated minimum distance off all samples to overall minimum), 
            or 'min_distance' (i.e. distance of current minimum to overall 
            minimum).
        :param str average_type: Type of averaging over study runs. Can be either 
            'mean' w.r.t. x-axis data or 'median' w.r.t. y-axis data
        :param bool invert: If True, the objective is multiplied by -1. 
            (Parameter not available for distance average types)
        :param bool log_scale: If True, the ouput of Y and sdev are determined as 
            mean and standard deviations of the natural logarithm of the 
            considered y_type.
        :param list minimum: Vector with minimum position. (Only available for 
             distance average types)
        :param list scales: Vector with positive weights for scaling distance in 
             different directions. (Only available for distance average types)
        :param str/int norm: Order of distance norm as defined in 
             numpy.linalg.norm. (Only available for distance average types)
        :param int num_samples: Number of samples on y-axis. (Only available for 
             median average type or time on x-axis)
        '''

        for key in ['minimum','scales']:
            try: kwargs[key] = json.dumps(kwargs[key])
            except KeyError: pass
            
        answer = self._post('benchmark', 'get_data', data=kwargs)
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not get benchmark data. Error: '
                                   + answer['error'])
        return answer['data']


    def set_objective(self,objective):
        """Set the objective function to be minimized. Example::
        
            def objective(x1,x2): 
                observation = study.new_observation()
                observation.add(x1**2+x2**2)
                return observation
            benchmark.set_objective(objective)
               
        .. note::  Call this function only after all studies have been added 
            to the benchmark.

        :param func objective: Function handle for a function of the 
            variable parameters that returns a corresponding Observation() object.
        """

        for study in self._studies: study.set_objective(objective)

    def run(self):
        """Run the benchmark after the objective has been set 
        (see :func:`~.benchmark.Benchmark.set_objective`). 
        Example::

            benchmark.run()

        """
        time_zero_benchmark = time.time()
        for study in self._studies:
            self.print_message('Running Study {}'.format(study.id),
                           message_type='remark',style='heading')
            for i in range(self.num_average):
                time_zero = time.time()
                self.print_message('Run {}/{}'.format(i+1,self.num_average))
                try: study.run()
                except EnvironmentError as err:
                    print("Study stopped due to error: {0}".format(err))
                self.add_study_results(study)
                timedelta = dt.timedelta(seconds=int(time.time() - time_zero))
                self.print_message('Study run finished after {}.'.format(timedelta))
        timedelta = dt.timedelta(seconds=int(time.time() - time_zero_benchmark))
        self.print_message('Benchmark finished after {}'.format(timedelta),
                                   style='heading')
