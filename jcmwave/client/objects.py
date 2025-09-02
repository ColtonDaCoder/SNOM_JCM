import sys
import json
import time

class Observation(object):

    def __init__(self):
        self._data = []
        self._finished = time.time()
    
    def add(self,value,derivative=None,uncertainty=None,type='objective',):
        """
        Add data to observation

        Parameters
        ----------
        value: Observed value of objective function
        derivative (optional): tuple (n1,n2,...) where ni is the order 
           of the derivative w.r.t the i-th variable for the observed value. 
           E.g. for value=1.0 and derivative=(1,0,...) the observation of
           d/dx1 objective(x1,x2,...) is added
           If derivative is None the objective itself is observed.
        uncertainty (optional): Uncertainty of the numerical value of the
           objective function
        type (optional): If type is 'objective' the observation belongs to the
           objective function. Observations of other types are just saved 
           and may be analyzed later. E.g. one may add information about
           the computational costs of the evaluation of the objective function.

        """
        if derivative is not None:
            try: basestring
            except: basestring=str
            if not isinstance(derivative, basestring): derivative = list(derivative)
            
        try: value = [float(v) for v in value]
        except: value = float(value)

        if uncertainty is not None:
            try: uncertainty = [float(u) for u in uncertainty]
            except: uncertainty = float(uncertainty)
        
        self._data.append(
            dict(derivative=derivative,value=value,type=type,uncertainty=uncertainty)
        )
        self._finished = time.time()
        
        return self

    @property
    def data(self): return self._data

    @property
    def finished(self): return self._finished
    
        
class Suggestion(object):

    def __init__(self,sample,id):
        self._created = time.time()
        self._id = id
        self._sample = sample

    @property
    def id(self): return self._id

    @property
    def created(self): return self._created
    
    @property
    def kwargs(self): return self._sample
    

