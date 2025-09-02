from .requestor import Requestor
from .objects import Observation, Suggestion
import time
import json
import threading
import warnings
import traceback
import datetime as dt
import atexit

class Study(Requestor):

    '''
    This class provides methods for controlling a numerical optimization study.
    Example::

         def objective(x1,x2): 
             observation = study.new_observation()
             observation.add(x1**2+x2**2)
             return observation
         study.set_parameters(max_iter=30, num_parallel=3)   

         #Start optimization loop
         study.set_objective(objective)   
         study.run()   

         #Alternatively, one can explicitely define the optimization loop
         def acquire(suggestion):
            try: observation = objective(suggestion.kwargs)
            except: study.clear_suggestion(suggestion.id, 'Objective failed')
            else: study.add_observation(observation, suggestion.id)

         while (not study.is_done()):
             suggestion = study.get_suggestion()
             t = Threading.thread(target=acquire, args=(suggestion,))
             t.start()       
    '''
    
    def __init__(self, host, study_id, session):
        super(Study, self).__init__(host=host,session=session)
        self.id = study_id
        self.objective = None
        self.num_failed = 0
        self.max_num_failed = 10
        self.lock = threading.Lock()
        self.deleted = False
        self.suggestions = dict()
        atexit.register(self._delete_on_server)

    def _delete_on_server(self):
        answer = self._post('study', 'delete')
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not delete study. Error: '
                                   + answer['error'])
        self.deleted = True
        
    def __del__(self):
        if not self.deleted: self._delete_on_server()
    
    def _post(self,object,operation,data=None):
        return super(Study, self).post(object,operation,self.id,data)

    def _get(self,object,type):
        return super(Study, self).get(object,self.id,type)

    def _run_task(self,task,purpose,data):
        # use as self._run_task('some_task','do something',data=kwargs)
        data['task'] = task
        error_msg = '{} failed. Error: '.format(purpose)
        answer = self._post('study', 'start_task', data=data)
        if (answer['status_code'] != 200):
            raise EnvironmentError(error_msg + answer['error'])
        task_id = answer['task_id']
        try:
          while True:
            answer = self._post('study', 'get_task_status', data={'task_id':task_id})
            if (answer['status_code'] != 200):
                raise EnvironmentError(error_msg + answer['error'])
            progress_msg = answer['progress_msg']
            status = answer['status']
            print('\r'+progress_msg+'      ',end="")
            if status == 'stopped': break
            time.sleep(1)

        except KeyboardInterrupt as e:
            answer = self._post('study', 'stop_task', data={'task_id':task_id})
            if (answer['status_code'] != 200):
                raise EnvironmentError(error_msg + answer['error'])

        answer = self._post('study', 'fetch_task_result',data={'task_id':task_id})
        print('')
        
        if (answer['status_code'] != 200):
            raise EnvironmentError(error_msg + answer['error'])
        return answer['result']

                  
    def set_parameters(self, **kwargs):
        """Sets parameters for the optimization run. Example::

            study.set_parameters(max_iter=100, num_parallel=5)
        
        :param int num_parallel: Number of parallel observations of the objective function
            (default: 1).

        :param int max_iter: Maximum number of evaluations of the objective 2
            function (default: inf).

        :param int max_time: Maximum optimization time in seconds (default: inf).

        .. note:: The full list of parameters depends on the chosen driver.
           For a parameter description, see the documentation of the driver.
        """

        for key in ['initial_samples','length_scales','warping_strengths',
                    'target_vector','uncertainty_vector','covariance_matrix',
                    'distribution','error_model_parameter_distribution',
                    'parameter_uncertainties', 'noise_variance','mutation',
                    'lattice_vector_lengths']:
            try: kwargs[key] = json.dumps(kwargs[key])
            except KeyError: pass
                    
        answer = self._post('study', 'set_parameters', data = kwargs)
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not set optimizations parameters. Error: '
                                   + answer['error'])

                
    def start_clock(self):        
        """The optimization stops after the time ``max_time`` 
            (see :func:`~.study.Study.set_parameters`). This function resets the 
            clock to zero. Example::

                study.start_clock()

            .. note:: The clock is also set to zero by calling set_parameters.
            
        """
        answer = self._post('study', 'start_clock')
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not start clock. Error: '
                                   + answer['error'])

    def info(self):
        """Get information about the status of the study. Example::
        
            info = study.info()
        
        :returns: Dictionary with entries
        
            :num_parallel: Number of parallel observations set.
            :is_done: True if the study has finished  (i.e. some stopping criterion was met)
            :status: Status message
            :open_suggestions: List of open suggestions
            :min_params: Parameters of the found minimum. 
                E.g. ``{'x1': 0.1, 'x2': 0.7}``
            :min_objective: Minimum value found.
            :num_dim: Number of variable dimensions of the search space.
         """
        answer = self._get('study','status')
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not retrieve information on study. Error: '
                                   + answer['error'])
        del answer['status_code']
        return answer
        
    def get_data_table(self):
        """Get table with data of the acquisitions. Example::

            data = study.get_data_table()
        
        :returns: Dictionary with entries
        
            :iteration: List of iteration number
            :datetime: List of dates and times of the creation of the
                corresponding suggestion.
            :cummin: List of cummulative minima for each iteration.
            :objective_value: List of the objective values aquired at each iteration.
            :parameters: Dictionary containing a list of parameter values for each
                parameter name.

        """
        answer = self._get('study', 'data_table')
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not get data table. Error: '
                                   + answer['error'])
        return answer

    def driver_info(self):
        """Get driver-specific information. Example::

            data = study.driver_info()
        
        :returns: Dictionary with multiple entries. For a description of
            the entries, see the documentation of the driver.
        """
        answer = self._get('study', 'driver_info')
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not get driver info. Error: '
                                   + answer['error'])
        return answer
    
    def is_done(self):
        """Checks if the study has finished. Example::

               if study.is_done(): break
        
        :returns: True if some stopping critereon set by 
            :func:`Study.set_parameters` was met. 

        .. note:: Before returning true, the function call waits until all open 
            suggestions have been added to the study.
        """
        info = self.info()
        if info['is_done']: self._wait_for_open_suggestions()
        return info['is_done']
    
    def _wait_for_open_suggestions(self):
        while True:
            info = self.info()
            if len(info['open_suggestions']) > 0: time.sleep(0.5)
            else: break
                
    def get_suggestion(self):
        """Get a new suggestion to be evaluated by the user. Example::
        
            suggestion = study.get_suggestion()
        
        :returns: ``Suggestion()`` object with properties 
           
            :id: Id of the suggestion
            :kwargs: Keyword arguments of the parameters. E.g. ``{'x1': 0.1, 'x2':0.2}``

        .. warning:: The function has to wait until the number of open suggestions is smaller
            than ``num_parallel`` before receiving a new suggestion. This can cause a deadlock
            if no observation is added by an independent thread.
        """
        while True:
            answer = self._post('suggestion','create')        
            if (answer['status_code'] == 202):
                time.sleep(0.5)
            else: break

        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not get suggestion. Error: '
                                   + answer['error'])
        s = Suggestion(sample=answer['sample'], id=answer['suggestion_id'])
        self.suggestions[s.id]= s
        return s
       
    def clear_suggestion(self, suggestion_id, message=''):
        """If the calculation of an objective value for a certain suggestion
        fails, the suggestion can be cleared from the study. Example::
        
            study.clear_suggestion(suggestion.id, 'Computation failed')

        .. note:: The study only creates ``num_parallel`` suggestions (see 
            :func:`~.study.Study.set_parameters`) until it waits for an 
            observation to be added (see :func:`~.study.Study.add_observation`) 
            or a suggestion to be cleared.
                 
        :param int suggestion_id: Id of the suggestion to be cleared.
        :param str message: An optional message that is printed out.
        """
        answer = self._post('suggestion', 'remove', data = {
            'suggestion_id': suggestion_id,
            'message' : message
        })  
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not clear suggestion. Error: '
                                   + answer['error'])
        del self.suggestions[suggestion_id]

    def get_minima(self, **kwargs):
        """Get a list of local minima and their sensitivities on the parameters 
        (i.e. their width) The minima are found using the Gaussian process only.
        Example::

            study.get_minima(n_output=10)

        .. note:: This function is only available for studies using a Bayesian driver,
            e.g. "BayesOptimization" (default driver).

        :param int n_samples: Number of initial samples for searching 
            (default: automatic determination).
        :param int n_output: Maximum number of minima that are returned (Default: 10)
        :param float epsilon: Parameter used for identifying identical minima (i.e. 
            minima with distance < length scale * epsilon)
            and minima with non-vanishing gradient (e.g. minima at the
            boundary of the search space) (default: 0.2)
        :param float delta: parameter used for approximating second derivatives 
            (default: 0.2)
        :param float min_dist: To increase the performance, it is possible to use
             a sparsified Gaussian process. One can define the minimal distance 
             between the datapoints in this Gaussian process in units of the
             length scale. (default: 0.0)
        :param int n_observations: Number of observations from the start used to build
             up the regression model. The model is configured with the corresponding 
             hyperparameters at the last added observations. 
             This parameter can be used to determine the convergence of the outcome 
             with the number of observations. The parameter cannot be used
             together with min_dist. (default: None, means
             all observations are taken into account)

        :returns: A list of dictionaries with information about local minimas
            with the objective value, the uncertaitny of the objective value, 
            the parameter values and the width in each parameter direction
            (i.e. standard deviation after a fit to a gaussian)

        """        
        return self._run_task('get_minima','get minima',data=kwargs)
        
    def run_mcmc(self, **kwargs):
        """Runs a Markov Chain Monte Carlo (MCMC) sampling over the posterior
        probability density of the parameters. This method should be run only after 
        the minimization of the likelihood is completed.
        Example::

            study.run()
            dist = [{name="param1", dist="normal", "mean"=1.0, "variance"=2.0},
                    {name="param2", dist="gamma", "alpha"=1.2, "beta"=0.5},
                    {name="param3", dist="uniform"}]
            study.set_parameters(distribution=dist)
            samples = study.run_mcmc()

        .. note:: The function is only available for the BayesLeastSquare driver.

        :param int num_walkers: Number of walkers (default: automaticcally chosen).
        :param int max_iter: Maximum absolute chain length (default: 1e4).
        :param int chain_length_tau: Maximum chain length in units of the
            correlation time tau (default: 100).
        :param bool multi_modal: If true, a more explorative sampling strategy
            is used (default: false).
        :param bool append: If true, the samples are appended to the samples of
            the previous MCMC run (default: false).
        :param float min_dist: To increase the performance of the sampling, 
             it is possible to us a sparsified Gaussian process. 
             One can define the minimal distance between the datapoints in this 
             Gaussian process in units of the length scalesss. (default: 0.0)
        :param float max_sigma_dist: If set, the sampling is restricted to a
             a distance max_sigma_dist * sigma to the maximum likelihood 
             estimate. E.g. max_digma_dist=3.0 means that only the 99.7% p
             robability region of each parameter is sampled. (default: inf)
        :param bool marginalize_uncertainties: If true, the mean value
            of the likelihood is determined by marginalizing over the 
            uncertainties of the Gaussian process regression. This is more
            reliable in parameter regions with fewer function acquisitions
            but leads also to a slower MCMC sampling. (default: false).

        :returns: A dictionary with the following entries:

            :samples: The drawn samples without "burnin" samples thinned by
                     half of the correlation time.
            :medians: The medians of all random parameters
            :lower_uncertainties: The distances between the medians and the 
                     16% quantile of all random parameters
            :upper_uncertainties: The distance between the medians and the 
                     84% quantile of all random parameters

        """

        return self._run_task('run_mcmc','MCMC sampling',data=kwargs)
       
    def predict(self, samples, derivatives=False):
        """Predict the value and the uncertainty of the objective function.
        Example::

            study.predict(samples=[[1,0,0],[2,0,1]])

        .. note:: This function is only available for studies using a Bayesian driver,
            e.g. "BayesOptimization" (default driver).

        :param list samples: List of samples, i.e. list with parameter values.
        :param bool derivatives: Whether derivatives of the means and uncertainties are
            computed.
        :param float min_dist: To increase the performance for making many
             predictions at once, it is possible to us a sparsified Gaussian process. 
             One can define the minimal distance between the datapoints in this 
             Gaussian process in units of the length scalesss. (default: 0.0)

        :returns: A dictionary with the respective lists of predictions 

        """
        
        answer = self._post('study', 'predict', data={
            'samples': json.dumps(samples),
            'derivatives': derivatives})
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not get prediction. Error: '
                                   + answer['error'])
        return {k: answer[k] for k in ('means', 'uncertainties',
                                    'derivatives', 'uncertainty_derivatives')}

    def integrate(self, funcs=None, **params):
        raise OSError('The integrate function is deprecated. '+
                      'Please, use get_statistics() instead.')
    
    def parameter_help(self):
        raise OSError('The function "parameter_help" is deprecated. '+
                  'Please, see the documentation for a description of the parameters.')

    def get_statistics(self, funcs=None, **params):
        """
        Determines statistice of the objective function which can be optionally 
        weighted with the functions "funcs". By default the probability density
        of the parameters is a uniform distribution in the whole parameter domain.
        Other parameter distributions can be defined via 
        study.set_parameters(distribution = dist).

        Example::
        
            study.set_parameters(distribution = [
             {name="param1", dist="normal", mean=1.0, variance=2.0},
             {name="param3", dist="uniform", domain=[0,1]},
             {name="param5", dist="beta", alpha=1.5, beta=0.8}])
            study.get_statistics(funcs=['1.0','x1','x1+x2'],abs_precision=0.001)

        .. note:: This function is only available for studies using a Bayesian driver,
            e.g. "BayesOptimization" (default driver).

        .. note:: For the Monta Carlo integration, only samples fulfilling the 
            contraints of the parameters are used.

        :param list|function funcs: A function string or a list of functions strings. 
            For functs=f the value of g(r) = objective(r)*f(r) is analyzed
            For functs=[f_1,f_2,...] a list of function [g_i(r)=objective(r)*f_i(r)] 
            is analyzed.
        :param float abs_precsion: The Monte Carlo integration is stopped when 
            the absolute precision of the mean value or the uncertainty of the 
            mean value is smaller than abs_precision. (Default: 1e-9)
        :param float rel_precsion: The Monte Carlo integration is stopped when 
            the relative precision of the mean value or the relative uncertainty 
            of the mean value is smaller than rel_precision. 
            (Default: 1e-3)
        :param float max_time: The Monte Carlo integration is stopped when the 
            time max_time has passed. (Default: inf)
        :param int max_iter: The Monte Carlo integration is stopped after max_iter 
            samples. (Default: 1e5)
        :param bool compute_uncertainity: Whether the uncertainty of the integral is
            computed based on the uncertainty of the Gaussian-process predictions. 
            (Default: True)
        :param float min_dist: To increase the performance, it is possible to use
             a sparsified Gaussian process. One can define the minimal distance 
             between the datapoints in this Gaussian process in units of the
             length scale. (default: 0.0)
        :param int n_observations: Number of observations from the start used to build
             up the regression model. The model is configured with the corresponding 
             hyperparameters at the last added observations. 
             This parameter can be used to determine the convergence of the outcome 
             with the number of observations. The parameter cannot be used
             together with min_dist. (default: None, means
             all observations are taken into account)

        :returns: A dictionary with the entries

            mean: Expectation value <g> of the (weighted) objective under the 
              parameter distribution
            variance: Variance <g^2> - <g>^2 of the (weighted) objective under the 
              parameter distribution
            uncertainty_mean: Uncertainty of the mean value determined from the 
              uncertainty of the Gaussian process regression.
            lower_quantile: 16% quantile of (weighted) objective values under the 
              parameter distribution
            median: 50% quantile of (weighted) objective values under the 
              parameter distribution
            upper_quantile: 84% quantile of (weighted) objective values under the 
              parameter distribution
            num_sampling_points: Number of sampling points that were used in the
              Monte Carlo integration. The numerical uncertainty of the computed
              mean value is Sqrt(variance/N).

        """
        data = dict(funcs = json.dumps(funcs), **params)
        return self._run_task('get_statistics','get statistics',data=data)        

    def optimize_hyperparameters(self, **params):        
        """Optimize the hyperparameters of the Gaussian process manually. 
        This is usually done automatically. See the documentation of the driver 
        'BayesOptimization' for parameters steering this process. 
        Example::

            study.optimize_hyperparameters()

        .. note:: This function is only available for specific drivers with
            a machine learning model, e.g. "BayesOptimization" (default driver).
            
        :param int n_samples: Number of initial start samples for optimization 
             (default: automatic determination)
        :param int n_observations: Number of observations from the start used to build
             up the regression model. This can be used if the hyperparameter optimiation
             for all observations takes too long. (default: all observations are 
             taken into account)

        :returns: A dictionary with entries 
             log-likelihood: Values of maximized log-likelihood
             hyperparameters: A list with the values of all optimized hyperparameters

        """
        return self._run_task('optimize_hyperparameters','optimize hyperparameters',
                              data=params)
    
    def new_observation(self):
        """Create a new observation object. Example::
        
            observation = study.new_observation()
            observation.add(1.2)
            observation.add(0.1, derivative='x1')
               
        :returns: ``Observation()`` object with the method ``add()`` that has the arguments
             
            :value: Observed value of objective function
            :derivative (optional): Name of the derivative paramter. E.g. for
                ``derivative='x1'``, the value is interpreted as the derivative 
                of the objective with respect to ``x1``.
        
        """
        return Observation()

    def add_observation(self,observation,suggestion_id=None,sample=None):
        """Adds an observation to the study. Example::
        
            study.add_observation(observation, suggestion.id)
        
        :param observation: ``Observation()`` object with added values 
            (see :func:`~.study.Study.new_observation`)
        :param int suggestion_id: Id of the corresponding suggestion if it exists. 
        :param dict sample: If the observation does not belong to an open suggestion,
             the corresponding sample must be provided. 
             E.g. ``{'x1': 0.1, 'x2': 0.2}``
                     
        """
        if not isinstance(observation,Observation):
            raise TypeError('observation -> expected Observation object. '+
                            'Check return value of objective function')
        
        if suggestion_id:
            computation_time = observation.finished - self.suggestions[suggestion_id].created
        else:
            computation_time = None
            
        answer = self._post('observation', 'create', data={
            'suggestion_id': suggestion_id,
            'sample': json.dumps(sample) if sample is not None else None,
            'observation': json.dumps(observation.data),
            'computation_time' : computation_time
        })
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not add observation. Error: '
                                   + answer['error'])
        if suggestion_id:
            del self.suggestions[suggestion_id]

    def add_many(self,samples,observations):
        """Adds many observations to the study. Example::
        
            study.add_observation(observations, samples)
        
        :param list samples: List of samples. 
             E.g. ``[{'x1': 0.1, 'x2': 0.2},{'x1': 0.3, 'x2': 0.4}]``
        :param list observations: List of ``Observation()`` objects for each sample
            (see :func:`~.study.Study.new_observation`)
                     
        """
        obs_data = [];
        for o in observations:
            if not isinstance(o,Observation):
                raise TypeError('observations -> expected Observation objects. '+
                                'Check return value of objective function')
            obs_data.append(o.data)
        answer = self._post('observation', 'create_many', data={
            'samples': json.dumps(samples),
            'observations': json.dumps(obs_data)
        })
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not add observations. Error: '
                                   + answer['error'])
        
    def set_objective(self,objective):
        """Set the objective function to be minimized. Example::
        
            def objective(x1,x2): 
                observation = study.new_observation()
                observation.add(x1**2+x2**2)
                return observation
            study.set_objective(objective)
               
        :param func objective: Function handle for a function of the 
            variable parameters that returns a corresponding Observation() object.
        """
        if self.objective is not None and objective != self.objective:
            warnings.warn('The objective was already set before. '
                          + 'Changing the objective for a study is not supported.',
                          RuntimeWarning)
            return
            
        self.objective = objective

    def run(self):
        """Run the acquisition loop after the objective has been set 
        (see :func:`~.study.Study.set_objective`). 
        The acquisition loop stops after a stopping
        critereon has been met (see :func:`~.study.Study.set_parameters`).
        Example::

            study.run()

        """
        if self.objective is None:
            raise EnvironmentError('The objective was not set')
        
        self.start_clock()
        try:
            while (not self.is_done()):
                if self.num_failed >= self.max_num_failed:
                    print('The previous {} computations failed. Stopping study.'.format(self.num_failed))
                    return
                suggestion = self.get_suggestion()
                t = threading.Thread(target=self._acquire, args=(suggestion,))
                t.daemon=True
                t.start()
        except KeyboardInterrupt as e:
            print('Study stopped.')


    def k_space_info(self, sigma):
        """Get information on a sample in k-space.
        Example::

            info = study.k_space_info(sigma=[0.1,0.5])

        .. note:: This function is only available for the driver "KSpaceRegression".

        :param list sigma: List of length two with x and y sigma coordinate.
             I.e. ``sigma = [kx/k0,ky/k0]`` with ``k0 = sqrt(kx^2+ky^2+kz^2)``.
        
        :returns: Dictionary with entries
        
            :bloch_family: List of sigma values of other members of the same 
                Bloch family.
            :max_entropy_bloch_family: Subset of Bloch family with the largest
                differential entropy of the Gaussian process posterior distribution.
            :bloch_family_in_symmetry_cone: List of sigma values of other members 
                of the same Bloch family that are inside the symmetry cone.
            :symmetry_family: List of all other sigma values obtained by performing 
                symmetry operations on sigma (e.g. reflections on symmetry axes).
            :mapped_to_symmetry_cone: sigma value in symmetry cone obtained by 
                performing symmetry operations on sigma (e.g. reflections on 
                symmetry axes).
        """
        
        answer = self._post('study', 'k_space_info', data={
            'sigma': json.dumps(sigma)})
        
        if (answer['status_code'] != 200):
            raise EnvironmentError('Could not get k-space information. Error: '
                                   + answer['error'])
        return {k: answer[k] for k in ('bloch_family', 'max_entropy_bloch_family',
                                       'symmetry_family', 'mapped_to_symmetry_cone')}
    
    
    def _acquire(self,suggestion):
        try:
            observation = self.objective(**suggestion.kwargs)
        except Exception as e:
            self.clear_suggestion(suggestion.id,
                    'Objective function failed with error: {}'.format(str(e))
            )
            print('The objective function raised the error: {}\n'.format(str(e))+
                          traceback.format_exc())
            raise
            with self.lock: self.num_failed += 1
            
        else:
            with self.lock: self.num_failed = 0
            self.add_observation(observation, suggestion.id)

 
