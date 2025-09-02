'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''


from jcmwave.__private.toolbox import NiL
from jcmwave.__private.toolbox import typename
from jcmwave.__private.system import FilePath
from jcmwave.__private.decorators import accepts
import jcmwave.data_tree as dt
import string


#

COORDINATE_RENAMING_STRINGS = set()
COORDINATE_RENAMING_STRINGS.add("-X:-Y:Z");
COORDINATE_RENAMING_STRINGS.add("-X:-Z:-Y");
COORDINATE_RENAMING_STRINGS.add("-X:Y:-Z");
COORDINATE_RENAMING_STRINGS.add("-X:Z:Y");
COORDINATE_RENAMING_STRINGS.add("-Y:-X:-Z");
COORDINATE_RENAMING_STRINGS.add("-Y:-Z:X");
COORDINATE_RENAMING_STRINGS.add("-Y:X:Z");
COORDINATE_RENAMING_STRINGS.add("-Y:Z:-X");
COORDINATE_RENAMING_STRINGS.add("-Z:-X:Y");
COORDINATE_RENAMING_STRINGS.add("-Z:-Y:-X");
COORDINATE_RENAMING_STRINGS.add("-Z:X:-Y");
COORDINATE_RENAMING_STRINGS.add("-Z:Y:X");
COORDINATE_RENAMING_STRINGS.add("X:-Y:-Z");
COORDINATE_RENAMING_STRINGS.add("X:-Z:Y");
COORDINATE_RENAMING_STRINGS.add("X:Y:Z");
COORDINATE_RENAMING_STRINGS.add("X:Z:-Y");
COORDINATE_RENAMING_STRINGS.add("Y:-X:Z");
COORDINATE_RENAMING_STRINGS.add("Y:-Z:-X");
COORDINATE_RENAMING_STRINGS.add("Y:X:-Z");
COORDINATE_RENAMING_STRINGS.add("Y:Z:X");
COORDINATE_RENAMING_STRINGS.add("Z:-X:-Y");
COORDINATE_RENAMING_STRINGS.add("Z:-Y:X");
COORDINATE_RENAMING_STRINGS.add("Z:X:Y");
COORDINATE_RENAMING_STRINGS.add("Z:Y:-X");

class Range:
#    @accepts(object, (int, float, NiL), (int, float, NiL), lowerBnD=(int, float, NiL), upperBnD=(int, float, NiL))
    def __init__(self, lowerBnD, upperBnd):
        self.first = lowerBnD
        self.second = upperBnd
    def __getitem__(self, key):
        if key==0:
            return self.first
        elif key==1:
            return self.second
        else:
            raise ValueError('Out of range.')

#

class PrimitiveSchema:
    
    @staticmethod
    def Create(*args, **kwargs):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')
    def Copy(self):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')
    def CreateTreePrimitive(self):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')
    def CheckRange(self, dataPrimitive):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')
    def TypeName(self):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')
    def RangeAsString(self):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')
    def HasDefault(self):
        raise RuntimeError('Class PrimitiveSchema should be used only through its subclasses.')

class NumberSchema(PrimitiveSchema):
    def __init__(self, default, dataRange, dtype):
        if not default==None: self._default = dtype(default)
        else: self._default=None;
        try:
            if self._default==dtype(NiL()): self._default=None;
        except: pass
        self._range = dataRange
        self._type = dtype
        self._typename = typename(dtype(0), False)
    @staticmethod
    def Create(default=None, dataRange=None, lowerBound=None, dtype=float):
        if dataRange!=None:
            pass
        elif lowerBound!=None:
            dataRange = Range(lowerBound, NiL())
        else:
            dataRange = Range(NiL(), NiL())
        return NumberSchema(default, dataRange, dtype)
    def Copy(self):
        rv = NumberSchema(self._default, self._range, self._type)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.NumberPrimitive(dtype=self._type)
        if not self._default==None:
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        value = dataPrimitive.GetValue()
        if isinstance(value, NiL):
            return False
        elif value==float('-inf'):
            if not (isinstance(self._range.first, NiL) or self._range.first==float('-inf')):
                return False
        elif value==float('inf'):
            if not (isinstance(self._range.second, NiL) or self._range.second==float('inf')):
                return False
        else:
            if not (isinstance(self._range.first, NiL) or self._range.first==float('-inf')):
                if value.real<self._range.first.real or value.imag<self._range.first.imag:
                    return False
            if not (isinstance(self._range.second, NiL) or self._range.second==float('inf')):
                if value.real>self._range.second.real or value.imag>self._range.second.imag:
                    return False
        return True
    def TypeName(self):
        return self._typename
    def RangeAsString(self):
        out = '['
        if isinstance(self._range.first, NiL) and isinstance(self._range.second, NiL):
            out += 'unrestricted'
        else:
            if isinstance(self._range.first, NiL) or self._range.first==float('-inf'):
                out += '-inf'
            else:
                out += str(self._range.first)
            out += ', '
            if isinstance(self._range.second, NiL) or self._range.second==float('inf'):
                out += 'inf'
            else:
                out += str(self._range.second)
        out += ']'
        return out
    def HasDefault(self):
        return not self._default==None;

class EnumSchema(PrimitiveSchema):
    def __init__(self, stringSet, default):
        self._default = str(default)
        self._stringSet = set(stringSet)
    @staticmethod
    def Create(stringSet=set(), default=NiL()):
        return EnumSchema(stringSet, default)
    def Copy(self):
        rv = EnumSchema(self._stringSet.copy(), self._default)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.StringPrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        value = dataPrimitive.GetValue()
        if len(self._stringSet)==0:
            return True
        if value in self._stringSet:
            return True
        else:
            return False
    def TypeName(self):
        return 'enum'
    def RangeAsString(self):
        return ', '.join(sorted(self._stringSet));
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class TensorSchema(PrimitiveSchema):
    def __init__(self, default=NiL(), rank=0):
        self._default = default
        self._rank = rank
        self._typename = str(rank)+'-Tensor'
    @staticmethod
    def Create(default=NiL(), rank=0):
        return TensorSchema(default, rank)
    def Copy(self):
        rv = TensorSchema(default=self._default, rank=self._rank)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.TensorPrimitive(rank=self._rank)
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        value = dataPrimitive.GetValue()
        if isinstance(value, NiL):
            return False
        elif len(value)!=int(3**int(self._rank)):
            return False
        return True
    def TypeName(self):
        return self._typename
    def RangeAsString(self):
        out = "[v_1, ..., v_"+str(int(3**int(self._rank)))+"]"
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class BooleanSchema(EnumSchema):
    def __init__(self, default):
        if default:
            default = 'yes'
        else:
            default = 'no'
        EnumSchema.__init__(self, set(['yes','no']), default)
    @staticmethod
    def Create(default=True):
        return BooleanSchema(default)
    def Copy(self):
        rv = BooleanSchema(self._default=='yes')
        return rv

class StringSchema(PrimitiveSchema):
    def __init__(self, default, rangeString=None):
        self._default = str(default)
        self._rangeString = rangeString
    @staticmethod
    def Create(default=NiL(),rangeString=None):
        return StringSchema(default,rangeString)
    def Copy(self):
        rv = StringSchema(self._default,self._rangeString)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.StringPrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        return True
    def TypeName(self):
        return 'string'
    def RangeAsString(self):
        out = '[]'
        if (self._rangeString):
            out = self._rangeString        
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class FileSchema(PrimitiveSchema):
    def __init__(self, default):
        self._default = default
    @staticmethod
    @accepts((FilePath, NiL), default=(FilePath, NiL))
    def Create(default=NiL()):
        return FileSchema(default)
    def Copy(self):
        rv = FileSchema(self._default)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.FilePrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        return True
    def TypeName(self):
        return 'file'
    def RangeAsString(self):
        out = '[]'
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class InputFileSchema(PrimitiveSchema):
    def __init__(self, default):
        self._default = default
    @staticmethod
    @accepts((FilePath, NiL), default=(FilePath, NiL))
    def Create(default=NiL()):
        return InputFileSchema(default)
    def Copy(self):
        rv = InputFileSchema(self._default)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.FilePrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        return True
    def TypeName(self):
        return 'input file'
    def RangeAsString(self):
        out = '[]'
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class OutputFileSchema(PrimitiveSchema):
    def __init__(self, default):
        self._default = default
    @staticmethod
    @accepts((FilePath, NiL), default=(FilePath, NiL))
    def Create(default=NiL()):
        return OutputFileSchema(default)
    def Copy(self):
        rv = OutputFileSchema(self._default)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.FilePrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        return True
    def TypeName(self):
        return 'output file'
    def RangeAsString(self):
        out = '[]'
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class TreePathSchema(PrimitiveSchema):
    def __init__(self, default):
        self._default = default
    @staticmethod
    @accepts((FilePath, NiL), default=(FilePath, NiL))
    def Create(default=NiL()):
        return TreePathSchema(default)
    def Copy(self):
        rv = TreePathSchema(self._default)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.FilePrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        return True
    def TypeName(self):
        return 'file'
    def RangeAsString(self):
        out = '[]'
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class VectorSchema(PrimitiveSchema):
    def __init__(self, upperBoundIndex, default=NiL(), dtype=float):
        self._default = default
        self._upperBoundIndex = upperBoundIndex
        self._typename, self._type = typename(dtype(0), True)
    @staticmethod
    def Create(upperBoundIndex=-1, default=NiL(), dtype=float):
        return VectorSchema(upperBoundIndex, default, dtype)
    def Copy(self):
        rv = VectorSchema(self._upperBoundIndex, self._default, self._type)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.VectorPrimitive(dtype=self._type)
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        value = dataPrimitive.GetValue()
        if isinstance(value, NiL):
            return False
        elif self._upperBoundIndex!=-1 and len(value)!=self._upperBoundIndex:
            return False
        return True
    def TypeName(self):
        return 'Vector<'+self._typename+'>'
    def RangeAsString(self):
        out = '[v_1, ...'
        if self._upperBoundIndex!=-1:
            out += ', v_'+str(self._upperBoundIndex)
        out += ']'
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class MatrixSchema(PrimitiveSchema):
    def __init__(self, nRows=0, nCols=0, default=NiL(), dtype=float):
        self._nRows=nRows
        self._nCols=nCols
        self._default = default
        self._typename, self._type = typename(dtype(0), True)
    @staticmethod
    def Create(nRows=0, nCols=0, default=NiL(), dtype=float):
        return MatrixSchema(nRows, nCols, default, dtype)
    def Copy(self):
        rv = MatrixSchema(nRows=self._nRows, nCols=self._nCols, default=self._default, dtype=self._type)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.MatrixPrimitive(dtype=self._type)
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        value = dataPrimitive.GetValue()
        if isinstance(value, NiL):
            return False
        elif (self._nRows*int(len(value)/self._nRows)!=len(value) or
              self._nCols*int(len(value)/self._nCols)!=len(value) or
              (self._nCols!=-1 and self._nRows!=-1) and
              (self._nCols*self._nRows!=len(value))):
            return False
        return True
    def TypeName(self):
        return 'Matrix<'+self._typename+'>'
    def RangeAsString(self):
        out = "[v_11, ..., v_1j; ...; v_i1, ...; v_ij]"
        if self._nRows!=-1:
            out += ', i<='+str(self._nRows)
        if self._nCols!=-1:
            out += ', j<='+str(self._nCols)
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class StringListSchema(VectorSchema):
    def __init__(self, upperBoundIndex, default=NiL()):
        self._default = default
        self._upperBoundIndex = upperBoundIndex
        self._typename = 'Vector<string>'
        self._type = str
    @staticmethod
    def Create(upperBoundIndex, default=NiL()):
        return StringListSchema(upperBoundIndex, default)
    def Copy(self):
        rv = StringListSchema(self._upperBoundIndex, self._default)
        return rv
    def TypeName(self):
        return self._typename
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.StringListPrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv

class EnumListSchema(VectorSchema):
    def __init__(self, upperBoundIndex, stringSet, default=NiL()):
        self._default = default
        self._stringSet = set(stringSet)
        self._upperBoundIndex = upperBoundIndex
        self._typename = 'Vector<enum>'
        self._type = str

    @staticmethod
    def Create(upperBoundIndex, stringSet=set(), default=NiL()):
        return EnumListSchema(upperBoundIndex, stringSet, default)
    def Copy(self):
        rv = StringListSchema(self._upperBoundIndex, self._stringSet, self._default)
        return rv
    def TypeName(self):
        return self._typename
    def RangeAsString(self):
       return VectorSchema.RangeAsString(self)+", v="+ '|'.join(sorted(self._stringSet));
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.StringListPrimitive()
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv

class TensorSchema(PrimitiveSchema):
    def __init__(self, default=NiL(), rank=0):
        self._default = default
        self._rank = rank
        self._typename = str(rank)+'-Tensor'
    @staticmethod
    def Create(default=NiL(), rank=0):
        return TensorSchema(default, rank)
    def Copy(self):
        rv = TensorSchema(default=self._default, rank=self._rank)
        return rv
    def CreateTreePrimitive(self):
        rv = dt.data_primitives.TensorPrimitive(rank=self._rank)
        if not isinstance(self._default, NiL):
            rv.SetValue(self._default)
        return rv
    def CheckRange(self, dataPrimitive):
        value = dataPrimitive.GetValue()
        if isinstance(value, NiL):
            return False
        elif len(value)!=int(3**int(self._rank)):
            return False
        return True
    def TypeName(self):
        return self._typename
    def RangeAsString(self):
        out = "[v_1, ..., v_"+str(int(3**int(self._rank)))+"]"
        return out
    def HasDefault(self):
        return not isinstance(self._default, NiL)

class RotationSchema(PrimitiveSchema):
    def __init__(self):
        self._typename = 'Rotation'
    @staticmethod
    def Create():
        return RotationSchema()
    def Copy(self):
        return RotationSchema()
    def CreateTreePrimitive(self):
        return dt.data_primitives.RotationPrimitive()
    def CheckRange(self, dataPrimitive):
        r = dataPrimitive.GetValue()
        if isinstance(r, NiL):
            return False
        det = ( 
             r.m[0][0]*(r.m[1][1]*r.m[2][2]-r.m[2][1]*r.m[1][2])
            -r.m[1][0]*(r.m[0][1]*r.m[2][2]-r.m[2][1]*r.m[0][2])
            +r.m[2][0]*(r.m[0][1]*r.m[1][2]-r.m[1][1]*r.m[0][2])
            )
        if abs(1.0-det)>1e-12:
            return False
        # test M^(-1) = MT
        idMat = [[0.0]*3]*3
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    idMat[i][j] += r.m[k][i]*r.m[k][j]
        for i in range(3):
            for j in range(3):
                if (i==j) and abs(idMat[i][j]-1.0*int(i==j))>1e-12:
                    return False
        return True
    def TypeName(self):
        return self._typename
    def RangeAsString(self):
        out = "[SO(3)]"
        return out
    def HasDefault(self):
        return False

class DictionarySchema(PrimitiveSchema):
    def __init__(self, valueSchema):
      self._valueSchema = valueSchema;
    @staticmethod
    def Create(valueSchema):
        return DictionarySchema(valueSchema)
    def Copy(self):
        return DictionarySchema(self._valueSchema.Copy())
    def CreateTreePrimitive(self):
        raise Exception("DictionarySchema", "dictionary primitive not implemented")
    def CheckRange(self, dataPrimitive):
        raise Exception("DictionarySchema", "dictionary primitive not implemented")
    def TypeName(self):
        return 'Dictionary<%s>' % (self._valueSchema.TypeName())
    def RangeAsString(self):
        return self._valueSchema.RangeAsString();
    def HasDefault(self):
        return False

#====================
#=== Unit Testing ===
#====================

if __name__=='__main__':
    import unittest
    #
    class Test_NumberSchema(unittest.TestCase):
        def setUp(self):
            self.schema = NumberSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = ((0,None,None), (0.0, None, None), (0+0j, None, None, complex), (0, None, 0), (0, Range(-5, NiL()), None))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = ((0,None,None), (0,Range(0,1),None))
            self.data['Copy']['arg_Vals'] = [tuple()]*2
            self.data['Copy']['return_Vals'] = [NumberSchema]*2
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = ((0,None,None),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.NumberPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = ((0,None,None),(0,Range(-5,5),None),(0,Range(NiL(), 5),None), (0,None,0))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.NumberPrimitive(-10,int),dt.data_primitives.NumberPrimitive(-5,int),dt.data_primitives.NumberPrimitive(0,int),dt.data_primitives.NumberPrimitive(5,int),dt.data_primitives.NumberPrimitive(10,int))]*4
            self.data['CheckRange']['return_Vals'] = ([True]*5,(False,True,True,True,False), (True,True,True,True,False),(False,False,True,True,True))
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = ((0,None,None,int),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('int',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = ((0,Range(-5,5),None),(0,Range(NiL(), 5.0),None), (0,None,0), (0,None,None))
            self.data['RangeAsString']['arg_Vals'] = [tuple()]*4
            self.data['RangeAsString']['return_Vals'] = ('[-5, 5]','[-inf, 5.0]','[0, inf]', '[unrestricted]')
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = ((0,Range(-5,5),None),)
            self.data['HasDefault']['arg_Vals'] = (tuple(),)
            self.data['HasDefault']['return_Vals'] = (True,)
        def test_Create(self):
            data = self.data['Create']
            for create_args in data['create']:
                self.schema.Create(*create_args)
        def test_Copy(self):
            data = self.data['Copy']
            for create_args, test_args, test_returns in zip(data['create'], data['arg_Vals'], data['return_Vals']):
                testInstance = self.schema.Create(*create_args)
                testInstanceCopy = testInstance.Copy(*test_args)
                self.assertTrue(isinstance(testInstanceCopy, test_returns))
        def test_CreateTreePrimitive(self):
            data = self.data['CreateTreePrimitive']
            for create_args, test_args, test_returns in zip(data['create'], data['arg_Vals'], data['return_Vals']):
                testInstance = self.schema.Create(*create_args)
                primitive = testInstance.CreateTreePrimitive(*test_args)
                self.assertTrue(isinstance(primitive, test_returns))
        def test_CheckRange(self):
            data = self.data['CheckRange']
            for create_args, test_args, test_returns in zip(data['create'], data['arg_Vals'], data['return_Vals']):
                testInstance = self.schema.Create(*create_args)
                for arg, rv in zip(test_args, test_returns):
                    boolVal = testInstance.CheckRange(arg)
                    self.assertEqual(boolVal, rv)
        def test_TypeName(self):
            data = self.data['TypeName']
            for create_args, test_args, test_returns in zip(data['create'], data['arg_Vals'], data['return_Vals']):
                testInstance = self.schema.Create(*create_args)
                thisTypeName = testInstance.TypeName(*test_args)
                self.assertEqual(thisTypeName, test_returns)
        def test_RangeAsString(self):
            data = self.data['RangeAsString']
            for create_args, test_args, test_returns in zip(data['create'], data['arg_Vals'], data['return_Vals']):
                testInstance = self.schema.Create(*create_args)
                stringRange = testInstance.RangeAsString(*test_args)
                self.assertEqual(stringRange, test_returns)
        def test_HasDefault(self):
            data = self.data['HasDefault']
            for create_args, test_args, test_returns in zip(data['create'], data['arg_Vals'], data['return_Vals']):
                testInstance = self.schema.Create(*create_args)
                thisHasDefault = testInstance.HasDefault(*test_args)
                self.assertEqual(thisHasDefault, test_returns)
    #
    class Test_EnumSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = EnumSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = (tuple(), (set(('s1','s2','s3')),), (set(('s1','s2','s3')), 's1'))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = (tuple(), (set(('s1','s2','s3')),), (set(('s1','s2','s3')), 's1'))
            self.data['Copy']['arg_Vals'] = [tuple()]*3
            self.data['Copy']['return_Vals'] = [EnumSchema]*3
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = (tuple(),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.StringPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = (tuple(), (set(('s1','s2','s3')),), (set(('s1','s2')), 's1'))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.StringPrimitive(False, 'a'), dt.data_primitives.StringPrimitive(False, 's1'), dt.data_primitives.StringPrimitive(True, 's3'))]*3
            self.data['CheckRange']['return_Vals'] = ([True]*3,(False,True,True), (False,True,False))
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = (tuple(),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('enum',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = (tuple(), (set(('s1','s2','s3')),), (set(('s1','s2')), 's1'))
            self.data['RangeAsString']['arg_Vals'] = [tuple()]*3
            self.data['RangeAsString']['return_Vals'] = ('[unrestricted]','[s1, s2, s3]','[s1, s2]')
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = (tuple(), (set(('s1','s2')), 's1'))
            self.data['HasDefault']['arg_Vals'] = (tuple(), tuple())
            self.data['HasDefault']['return_Vals'] = (False, True)
    class Test_StringSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = StringSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = (tuple(), ('default',))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = (tuple(), ('default',))
            self.data['Copy']['arg_Vals'] = [tuple()]*2
            self.data['Copy']['return_Vals'] = [StringSchema]*2
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = (tuple(),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.StringPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = (tuple(), ('default',))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.StringPrimitive(False, 'a'), dt.data_primitives.StringPrimitive(False, 's1'), dt.data_primitives.StringPrimitive(True, 's3'))]*2
            self.data['CheckRange']['return_Vals'] = [[True]*3]*2
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = (tuple(),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('string',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = (tuple(),)
            self.data['RangeAsString']['arg_Vals'] = (tuple(),)
            self.data['RangeAsString']['return_Vals'] = ('[]',)
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = (tuple(), ('default',))
            self.data['HasDefault']['arg_Vals'] = (tuple(), tuple())
            self.data['HasDefault']['return_Vals'] = (False, True)
    class Test_FileSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = FileSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = (tuple(), (FilePath('/a/b/c'),))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = (tuple(), (FilePath('/a/b/c'),))
            self.data['Copy']['arg_Vals'] = [tuple()]*2
            self.data['Copy']['return_Vals'] = [FileSchema]*2
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = (tuple(),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.FilePrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = (tuple(), (FilePath('/a/b/c'),))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.FilePrimitive(False, FilePath('/a')), dt.data_primitives.FilePrimitive(True, FilePath('a/b')))]*2
            self.data['CheckRange']['return_Vals'] = [[True]*2]*2
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = (tuple(),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('file',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = (tuple(),)
            self.data['RangeAsString']['arg_Vals'] = (tuple(),)
            self.data['RangeAsString']['return_Vals'] = ('[]',)
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = (tuple(), (FilePath('/a/b/c'),))
            self.data['HasDefault']['arg_Vals'] = (tuple(), tuple())
            self.data['HasDefault']['return_Vals'] = (False, True)
    class Test_VectorSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = VectorSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = ((4,), (4,NiL(),int), (4,[0]*4,int))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = ((4,), (4,NiL(),int), (4,[0]*4,int))
            self.data['Copy']['arg_Vals'] = [tuple()]*3
            self.data['Copy']['return_Vals'] = [VectorSchema]*2
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = ((4,),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.VectorPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = ((1,NiL(),float), (2,NiL(),int), (-1,NiL(),complex))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.VectorPrimitive((1,),float), dt.data_primitives.VectorPrimitive((1,2), float), dt.data_primitives.VectorPrimitive((1,2,3), complex))]*3
            self.data['CheckRange']['return_Vals'] = [(True, False, False),(False,True,False),(True,True,True)]
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = ((1,),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('Vector<float>',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = ((3,),(-1,))
            self.data['RangeAsString']['arg_Vals'] = (tuple(),)
            self.data['RangeAsString']['return_Vals'] = ('[v_1, ..., v_3]','[v_1, ...]')
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = ((3,),(-1,[1,2,3]))
            self.data['HasDefault']['arg_Vals'] = (tuple(), tuple())
            self.data['HasDefault']['return_Vals'] = (False, True)
    class Test_MatrixSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = MatrixSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = ((3,3,NiL(),float),)
            self.data['Copy'] = {}
            self.data['Copy']['create'] = ((3,3,NiL(),float),)
            self.data['Copy']['arg_Vals'] = [tuple()]
            self.data['Copy']['return_Vals'] = [MatrixSchema]
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = ((3,3,NiL(),float),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.MatrixPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = ((3,3,NiL(),float),)
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.MatrixPrimitive((1,2,3,4,5,6,7,8,9),float), dt.data_primitives.MatrixPrimitive((1,2,3,4,5,6,7,8),float))]
            self.data['CheckRange']['return_Vals'] = [(True, False)]
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = ((3,3,NiL(),float),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('Matrix<float>',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = ((3,3,NiL(),float),(-1,3,NiL(),float),(3,-1,NiL(),float),(-1,-1,NiL(),float))
            self.data['RangeAsString']['arg_Vals'] = (tuple(),tuple(),tuple(),tuple())
            self.data['RangeAsString']['return_Vals'] = ('[v_11, ..., v_1j; ...; v_i1, ...; v_ij], i<=3, j<=3','[v_11, ..., v_1j; ...; v_i1, ...; v_ij], j<=3','[v_11, ..., v_1j; ...; v_i1, ...; v_ij], i<=3', '[v_11, ..., v_1j; ...; v_i1, ...; v_ij]')
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = ((3,3,NiL(),float),)
            self.data['HasDefault']['arg_Vals'] = (tuple(),)
            self.data['HasDefault']['return_Vals'] = (False,)
    class Test_StringListSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = StringListSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = ((4,), (4,NiL()), (4,['0']*4))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = ((4,), (4,NiL()), (4,['0']*4))
            self.data['Copy']['arg_Vals'] = [tuple()]*3
            self.data['Copy']['return_Vals'] = [StringListSchema]*3
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = ((4,), (4,NiL()), (4,['0']*4))
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.StringListPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = ((4,), (2,NiL()), (2,['0']*2))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.StringListPrimitive(('1',)), dt.data_primitives.StringListPrimitive(('1','2')), dt.data_primitives.StringListPrimitive(('1','2')))]*3
            self.data['CheckRange']['return_Vals'] = [(False, False, False),(False,True,True),(False,True,True)]
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = ((4,),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('Vector<string>',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = ((4,), (-1,NiL()))
            self.data['RangeAsString']['arg_Vals'] = (tuple(),tuple())
            self.data['RangeAsString']['return_Vals'] = ('[v_1, ..., v_4]','[v_1, ...]')
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = ((4,), (4,NiL()), (4,['0']*4))
            self.data['HasDefault']['arg_Vals'] = (tuple(), tuple(), tuple())
            self.data['HasDefault']['return_Vals'] = (False, False, True)
    class Test_TensorSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = TensorSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = ((NiL(),0), ([1,2,3],1), (NiL(),2))
            self.data['Copy'] = {}
            self.data['Copy']['create'] = ((NiL(),0), ([1,2,3],1), (NiL(),2))
            self.data['Copy']['arg_Vals'] = [tuple()]*3
            self.data['Copy']['return_Vals'] = [TensorSchema]*3
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = ((NiL(),0),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.TensorPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = ((NiL(),0), ([1,2,3],1), (NiL(),2))
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.TensorPrimitive(dt.data_primitives.Tensor3D([1]),0),dt.data_primitives.TensorPrimitive(dt.data_primitives.Tensor3D([1,2,3]),1),dt.data_primitives.TensorPrimitive(dt.data_primitives.Tensor3D(list(range(9))),3))]*3
            self.data['CheckRange']['return_Vals'] = [(True, False, False),(False,True,False),(False,False,True)]
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = ((NiL(),0), ([1,2,3],1), (NiL(),2))
            self.data['TypeName']['arg_Vals'] = (tuple(),tuple(),tuple())
            self.data['TypeName']['return_Vals'] = ('0-Tensor','1-Tensor','2-Tensor')
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = ((NiL(),0), ([1,2,3],1), (NiL(),2))
            self.data['RangeAsString']['arg_Vals'] = (tuple(),tuple())
            self.data['RangeAsString']['return_Vals'] = ('[v_1, ..., v_1]','[v_1, ..., v_3]','[v_1, ..., v_9]')
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = ((NiL(),0), ([1,2,3],1), (NiL(),3))
            self.data['HasDefault']['arg_Vals'] = (tuple(), tuple(), tuple())
            self.data['HasDefault']['return_Vals'] = (False, True, False)
    class Test_RotationSchema(Test_NumberSchema):
        def setUp(self):
            self.schema = RotationSchema
            self.data = {}
            self.data['Create'] = {}
            self.data['Create']['create'] = (tuple(),)
            self.data['Copy'] = {}
            self.data['Copy']['create'] = (tuple(),)
            self.data['Copy']['arg_Vals'] = [tuple()]
            self.data['Copy']['return_Vals'] = [RotationSchema]
            self.data['CreateTreePrimitive'] = {}
            self.data['CreateTreePrimitive']['create'] = (tuple(),)
            self.data['CreateTreePrimitive']['arg_Vals'] = (tuple(),)
            self.data['CreateTreePrimitive']['return_Vals'] = (dt.data_primitives.RotationPrimitive,)
            self.data['CheckRange'] = {}
            self.data['CheckRange']['create'] = (tuple(),)
            self.data['CheckRange']['arg_Vals'] = [(dt.data_primitives.RotationPrimitive(dt.data_primitives.Rotation([[0,1,0],[-1,0,0],[0,0,1]])),dt.data_primitives.RotationPrimitive(dt.data_primitives.Rotation([[1,1,0],[1,0,0],[0,0,1]])))]
            self.data['CheckRange']['return_Vals'] = [(True, False)]
            self.data['TypeName'] = {}
            self.data['TypeName']['create'] = (tuple(),)
            self.data['TypeName']['arg_Vals'] = (tuple(),)
            self.data['TypeName']['return_Vals'] = ('Rotation',)
            self.data['RangeAsString'] = {}
            self.data['RangeAsString']['create'] = (tuple(),)
            self.data['RangeAsString']['arg_Vals'] = (tuple(),)
            self.data['RangeAsString']['return_Vals'] = ('[SO(3)]',)
            self.data['HasDefault'] = {}
            self.data['HasDefault']['create'] = (tuple(),)
            self.data['HasDefault']['arg_Vals'] = (tuple(),)
            self.data['HasDefault']['return_Vals'] = (False,)
    unittest.main()
