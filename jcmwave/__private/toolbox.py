'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

from jcmwave.__private.decorators import *
#from builtins import str

class NiL(str):
    real = float('nan')
    imag = float('nan')
    def __add__(self, other):
        return self
    def __radd__(self, other):
        return self
    def __iadd__(self, other):
        pass
    def __sub__(self, other):
        return self
    def __rsub__(self, other):
        return self
    def __isub__(self, other):
        pass
    def __mul__(self, other):
        return self
    def __rmul__(self, other):
        return self
    def __imul__(self, other):
        pass
    def __div__(self, other):
        return self
    def __rdiv__(self, other):
        return self
    def __idiv__(self, other):
        pass
    def __getitem__(self, k):
        return self
    def __setitem__(self,k,v):
        pass
    def __len__(self):
        return float('nan')
    def __eq__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __ne__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __gt__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __ge__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __lt__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __le__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __cmp__(self, other):
        raise ValueError("Unable to compare to NiL-type.")
    def __str__(self):
        return self
    def __repr__(self):
        return self

def getDerivedNiL(obj):
    class nil_obj(NiL, type(obj)):
        pass
    r = nil_obj()
    return r

def isNiL(obj):
    return isinstance(obj, NiL)

@accepts((int, float, complex), bool, doReturnType=bool)
def typename(obj, doReturnType=False):
    if isinstance(obj, int):
        if doReturnType:
            return 'int', int
        else:
            return 'int'
    if isinstance(obj, float):
        if doReturnType:
            return 'float', float
        else:
            return 'float'
    if isinstance(obj, complex):
        if doReturnType:
            return 'complex', complex
        else:
            return 'complex'

class AsciiVector:
    @accepts(object, (str), delimiter=(str))
    def __init__(self, delimiter=':'):
        self._delimiter = delimiter
        self._data = []
    def Copy(self):
        cp = AsciiVector(self.GetDelimiter())
        cp.Clear()
        cp.Append(self)
        return cp
    def GetDelimiter(self):
        return self._delimiter
    @accepts(object, (str), nextItem=(str))
    def PushBack(self, nextItem):
        self._data.append(nextItem)
    def PopBack(self):
        return self._data.pop()
    def Append(self, otherAsciiVector):
        if not isinstance(otherAsciiVector, AsciiVector):
            raise TypeError('Append only accepts objects of type "AsciiVector".')
        self._data.extend(otherAsciiVector)
    def Clear(self):
        self._data = []
    def Size(self):
        return len(self)
    @accepts(object, int, i=int)
    def At(self, i):
        return self._data[i]
    @accepts(object, (str), set, asciiPath=(str), delimiters=set)
    def Import(self, asciiPath, delimiters=set()):
        if len(delimiters)==0:
            delimiters.add(self._delimiter)
        buffer = ''
        self._data = []
        for ic in range(len(asciiPath)):
            if not asciiPath[ic] in delimiters:
                buffer += asciiPath[ic]
            else:
                self._data.append(buffer)
                buffer = ''
        if len(buffer)>0:
            self._data.append(buffer)
    def Export(self):
        return self._delimiter.join(self._data)
    def ExportParent(self):
        return self._delimiter.join(self._data[:-1])
    def __eq__(self, other):
        if not isinstance(other, AsciiVector):
            raise TypeError('Can only compare to AsciiVector type.')
        if len(self)!=len(other):
            return False
        for ii in range(len(self)):
            if self.At(ii)!=other.At(ii):
                return False
        return True
    def __ne__(self, other):
        return (not self.__eq__(other))
    def __len__(self):
        return len(self._data)
    def __getitem__(self,ii):
        return self._data[ii]
    def __str__(self):
        return self.Export()
    def __repr__(self):
        return self.Export()
    def __hash__(self):
        return hash(self.Export())

