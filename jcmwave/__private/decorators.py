'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

class accepts:
    def __init__(self, *args, **kwargs):
        self.accepted_unnamed = args
        self.accepted_named = kwargs
    def __call__(self,f):
        def new_f(*args, **kwargs):
            if len(args)>(len(self.accepted_unnamed)):
                raise AttributeError("Wrong number of arguments.")
            for iarg in range(len(args)):
                if not isinstance(args[iarg], self.accepted_unnamed[iarg]):
                    raise TypeError("Wrong argument type: Type of argument number "+
                                      str(iarg)+" should be in \""
                                      +str(self.accepted_unnamed[iarg])
                                      +"\" but is of type \""+str(type(args[iarg]))+"\"")
            for kwargKey in kwargs.keys():
                if kwargKey not in self.accepted_named:
                    continue
                if not isinstance(kwargs[kwargKey], self.accepted_named[kwargKey]):
                    raise TypeError("Wrong argument type: Type of \""
                                      +kwargKey+"\" should be in \""
                                      +str(self.accepted_named[kwargKey])
                                      +"\" but is of type \""+str(type(kwargs[kwargKey]))+"\"")
            return f(*args, **kwargs)
        new_f.__name__ = f.__name__
        return new_f

class returns:
    def __init__(self,returnType):
        self.returnType = returnType
    def __call__(self,f):
        def new_f(*args,**kwargs):
            returnValue = f(*args, **kwargs)
            if not isinstance(returnValue, self.returnType):
                raise ValueError('Unexpected return type "'+str(type(returnValue))+'". "'+str(self.returnType)+'" expected.')
            return returnValue
        new_f.__name__ = f.__name__
        return new_f

class cached:
    def __init__(self, cacheSize):
        self.cacheSize = cacheSize
    def __call__(self, f):
        class f_obj:
            def __init__(self, f, cacheSize):
                self.__inout = {}
                self.__counter = 0
                self.__func = f
                self.__cacheSize = cacheSize
            def __call__(self, *args, **kwargs):
                self.__counter += 1
                if self.__counter>=10*self.__cacheSize:
                    for k in self.__inout.keys():
                        if self.__inout[k][1]<3:
                            self.__inout.pop(k)
                if len(args)==0:
                    args = []
                if len(kwargs)==0:
                    hashTuple = tuple(args)
                else:
                    hashTuple = tuple(list(args).extend(list(kwargs.values())))
                hv = hash(hashTuple)
                if hv in self.__inout:
                    value = self.__inout[hv][0]
                    self.__inout[hv][1] += 1
                else:
                    value = self.__func(*args, **kwargs)
                    if len(self.__inout)<self.__cacheSize:
                        self.__inout[hv] = [value, 0]
                return value
            def cacheSize(self):
                return len(self.__inout)
            def clearCache(self):
                self.__counter = 0
                self.__inout = {}
        new_f = f_obj(f, self.cacheSize)
        new_f.__name__ = f.__name__
        return new_f
