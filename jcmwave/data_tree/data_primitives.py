'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

from jcmwave.__private.decorators import *
from .data_tree_exceptions import *
import jcmwave.__private.toolbox as toolbox
from jcmwave.__private.system import FilePath
from . import parser

def prettyT(t):
  if (type(t)==complex): 
    if (t.imag==0): return str(t.real);
    else: return '('+str(t.real)+', '+str(t.imag)+')'
  return str(t);

    

class Tensor3D:
    @accepts(object, (list,tuple), tensorData=(list,tuple))
    def __init__(self, tensorData=[]):
        self.entries = []
        for dat in tensorData:
            self.entries.append(complex(dat))
    @accepts(object, int, ii=int)
    def __getitem__(self, ii):
        if ii>len(self.entries)-1 or ii<0:
            raise IndexError('Index out of range.')
        return self.entries[ii]
    @accepts(object, int, (int, float, complex), ii=int, v=(int, float, complex))
    def __setitem__(self, ii, v):
        if ii>len(self.entries)-1 or ii<0:
            raise IndexError('Index out of range.')
        self.entries[ii] = complex(v)
    @accepts(object, int, size=int)
    def Resize(self, size):
        if len(self.entries)==size:
            pass
        elif len(self.entries)<size:
            self.entries.extend([complex(0)]*(size-len(self.entries)))
        elif size<=0:
            self.entries = []
        elif size<len(self.entries):
            self.entries = self.entries[0:size]
        else:
            raise Exception('Indexing bug.')
    def Data(self):
        return self.entries
    def __len__(self):
        return len(self.entries)
    def __eq__(self, other):
        if isinstance(other, Tensor3D):
            if len(self)==len(other) and all([self[ii]==other[ii] for ii in range(len(self))]):
                return True
        return False
    def __ne__(self, other):
        return (not self.__eq__(other))


class Rotation:
    def __init__(self, m=None):
        self.m = [list([0.0]*3) for ii in range(3)]
        if m!=None:
            for ii in range(3):
                for jj in range(3):
                    self.m[ii][jj] = float(m[ii][jj])
    def __getitem__(self, ii):
        jj = None
        if isinstance(ii, tuple):
            if len(ii)==0:
                raise IndexError('Invalid index.')
            if len(ii)>1:
                jj = int(ii[1])
            ii = int(ii[0])
        else:
            ii = int(ii)
        if jj is None:
            return self.m[ii]
        else:
            return self.m[ii][jj]
    def __setitem__(self, ii, value):
        jj = None
        if isinstance(ii, tuple):
            if len(ii)==0:
                raise IndexError('Invalid index.')
            if len(ii)>1:
                jj = int(ii[1])
            ii = int(ii[0])
        else:
            ii = int(ii)
        if jj!=None:
            self.m[ii][jj] = float(value)
        else:
            for jj in range(len(self.m[ii])):
                self.m[ii][jj] = float(value)
    def __eq__(self, other):
        for ii in range(3):
            for jj in range(3):
                if not self.m[ii][jj]==other[ii][jj]:
                    return False
        return True
    def __ne__(self, other):
        return (not self.__eq__(other))

#=======================
#=== Tree Primitives ===
#=======================

class TreePrimitive:
    def TypeName(self):
        return 'TreePrimitive'
    @staticmethod
    def Create():
        raise Exception('TreePrimitive should only be used through subclasses.')
    def Copy(self):
        raise Exception('TreePrimitive should only be used through subclasses.')
    def Write(self):
        raise Exception('TreePrimitive should only be used through subclasses.')
    def Read(self, reader):
        raise Exception('TreePrimitive should only be used through subclasses.')
    def Nil(self):
        raise Exception('TreePrimitive should only be used through subclasses.')
    @staticmethod
    def IsNiL(value):
        raise Exception('TreePrimitive should only be used through subclasses.')
    def GetValue(self):
        raise Exception('TreePrimitive should only be used through subclasses.')
    def SetValue(self, newVal):
        raise Exception('TreePrimitive should only be used through subclasses.')

class NumberPrimitive(TreePrimitive):
    @accepts(TreePrimitive, (int, float, complex), type, value=(int, float, complex), dtype=type)
    def __init__(self, value=0, dtype=float):
        self.__type = dtype
        self.__typename = toolbox.typename(dtype())
        self.__value = dtype(value)
    @staticmethod
    def Create(value=0, dtype=float):
        return NumberPrimitive(value, dtype)
    def Copy(self):
        return NumberPrimitive(self.__value, self.__type)
    def TypeName(self):
        return self.__typename
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (int, float, complex), newVal=(int, float, complex))
    def SetValue(self, newVal):
        self.__value = self.__type(newVal)
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        val, success = reader.Get(self.__type)
        if not success:
            return False
        self.__value = val
        return True
    def Write(self):
        return prettyT(self.__value);


class StringPrimitive(TreePrimitive):
    @accepts(TreePrimitive, bool, (str), quotMarks=bool, strArg=(str))
    def __init__(self, quotMarks=False, strArg=''):
        self.__quotMarks = quotMarks
        self.__value = strArg
    @staticmethod
    def Create(quotMarks=False, strArg=''):
        return StringPrimitive(quotMarks, strArg)
    def Copy(self):
        return StringPrimitive(self.__quotMarks, self.__value)
    def TypeName(self):
        return 'string'
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (str), newVal=(str))
    def SetValue(self, newVal):
        self.__value = newVal
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        hasQuotMarks = reader.TestToken('"')
        if hasQuotMarks:
            self.__quotMarks = True
        readValue, success = parser.ReadString(type(self.__value), reader, self.__quotMarks)
        if not success:
            return False
        self.__value = readValue
        return True        
    def Write(self):
        if not self.__quotMarks:
            return str(self.__value)
        else:
            return '"'+self.__value+'"'

class FilePrimitive(TreePrimitive):
    @accepts(TreePrimitive, bool, FilePath, quotMarks=bool, filePath=FilePath)
    def __init__(self, quotMarks=False, filePath=FilePath()):
        self.__quotMarks = quotMarks
        self.__value = filePath
    @staticmethod
    def Create(quotMarks=False, filePath=FilePath()):
        return FilePrimitive(quotMarks, filePath)
    def Copy(self):
        return FilePrimitive(self.__quotMarks, self.__value.Copy())
    def TypeName(self):
        return 'file'
    def NiL(self):
        return toolbox.getDerivedNiL(FilePath())
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (str, FilePath), newVal=(str, FilePath))
    def SetValue(self, newVal):
        if isinstance(newVal, str):
            self.__value = FilePath(newVal)
        elif isinstance(newVal, FilePath):
            self.__value = newVal          
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        readValue, success = parser.ReadString(str, reader, quotMarks=True)
        if not success:
            return False
        self.__value = FilePath(readValue, universal=True)
        return True
    def Write(self):
        return '"'+str(self.__value.Export())+'"'
    def PathAsString(self):
        return self.__value # @TODO: replace once a file path object exists (now string)

class TreePath(toolbox.AsciiVector):
    @accepts(object, (str), data=(str))
    def __init__(self, data=str('')):
        self._delimiter = '/'
        self._data = []
        self.Import(data)
        self._data = [x for x in self._data if len(x)>0]
    def Copy(self):
        cp = TreePath(data=self.Path())
        return cp
    def Tag(self):
        return self.At(-1)
    def Section(self):
        return self.ExportParent()+self._delimiter
    def Path(self):
        return self.Export()
    def __eq__(self, other):
            return AsciiVector.__eq__(self, other)
    def __ne__(self, other):
        return (not self.__eq__(other))

class TreePathPrimitive(TreePrimitive):
    @accepts(TreePrimitive, TreePath, treePath=TreePath())
    def __init__(self, treePath=TreePath()):
        self.__value = treePath
    @staticmethod
    def Create(treePath=TreePath()):
        return TreePathPrimitive(treePath)
    def Copy(self):
        return TreePathPrimitive(self.__value.Copy())
    def TypeName(self):
        return 'TreePath'
    def NiL(self):
        return toolbox.getDerivedNiL(TreePath())
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (str, TreePath), newVal=(str, TreePath))
    def SetValue(self, newVal):
        if isinstance(newVal, str):
            self.__value = TreePath(newVal)
        elif isinstance(newVal, TreePath):
            self.__value = newVal          
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        readValue, success = parser.ReadString(str, reader, quotMarks=False)
        if not success:
            return False
        self.__value = TreePath(readValue)
        return True
    def Write(self):
        return str(self.__value.Export())
    def PathAsString(self):
        return self.__value # @TODO: replace once a file path object exists (now string)

class VectorPrimitive(TreePrimitive):
    @accepts(TreePrimitive, (list, tuple), type, value=(list, tuple), dtype=type)
    def __init__(self, value=tuple(), dtype=float):
        self.__value = list(value)
        self.__type = dtype
        self.__typename = toolbox.typename(dtype(0))
        self.__update()
    def __update(self):
        for ii in range(len(self.__value)):
            self.__value[ii] = self.__type(self.__value[ii])
    @staticmethod
    def Create(value=tuple(), dtype=float):
        return VectorPrimitive(value, dtype)
    def Copy(self):
        return VectorPrimitive([xx for xx in self.__value], self.__type)
    def TypeName(self):
        return 'Vector<'+str(self.__typename)+'>'
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (list, tuple), newVal=(list, tuple))
    def SetValue(self, newVal):
        self.__value = list(newVal)
        self.__update()
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        entryList, success = parser.ParseNumberVectorAsList(self.__type, reader)
        if not success:
            entryList, success = parser.ParseLegacyTensorFormat(self.__type, rank=1, reader=reader)
            if not success:
                return False
        pot = 1
        if reader.SkipToken('^'):
            pot, success = reader.Get(int)
            if not success:
                return False
        self.__value = [entry**pot for entry in entryList]
        return True
    def Write(self):
        rv = '['
        for ii in range(len(self.__value)-1):
            rv+=prettyT(self.__value[ii]);
            rv += ', '
        if len(self.__value)>0:
            rv += prettyT(self.__value[len(self.__value)-1])
        rv += ']'
        return rv

class MatrixPrimitive(TreePrimitive):
    @accepts(TreePrimitive, (list, tuple), type, value=(list, tuple), dtype=type)
    def __init__(self, value=tuple(), dtype=float):
        self.__value = list(value)
        self.__type = dtype
        self.__typename = toolbox.typename(dtype(0))
        self.__update()
    def __update(self):
        for ii in range(len(self.__value)):
            self.__value[ii] = self.__type(self.__value[ii])
    @staticmethod
    def Create(value=tuple(), dtype=float):
        return MatrixPrimitive(value, dtype)
    def Copy(self):
        return MatrixPrimitive([xx for xx in self.__value], self.__type)
    def TypeName(self):
        return 'Matrix<'+str(self.__typename)+'>'
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (list, tuple), newVal=(list, tuple))
    def SetValue(self, newVal):
        self.__value = list(newVal)
        self.__update()
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        entryList, success = parser.ParseNumberVectorAsList(self.__type, reader)
        if not success:
            return False
        self.__value = entryList
        return True
    def Write(self):
        rv = '['
        for ii in range(len(self.__value)-1):
            rv += prettyT(self.__value[ii])
            rv += ', '
        rv += prettyT(self.__value[len(self.__value)-1])
        rv += ']'
        return rv

class StringListPrimitive(VectorPrimitive):
    @accepts(TreePrimitive, (list, tuple), value=(list, tuple))
    def __init__(self, value=tuple()):
        self.__value = list(value)
        self.__update()
    def __update(self):
        for ii in range(len(self.__value)):
            self.__value[ii] = str(self.__value[ii])
    @staticmethod
    def Create(value=tuple()):
        return StringListPrimitive(value)
    def Copy(self):
        return StringListPrimitive([xx for xx in self.__value])
    def TypeName(self):
        return 'Vector<string>'
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (list, tuple), newVal=(list, tuple))
    def SetValue(self, newVal):
        self.__value = list(newVal)
        self.__update()
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        entryList = []
        stopTokens = set([',', ']', ':'])
        if not reader.SkipToken('['):
            return False
        while True:
            if reader.SkipToken(']'):
                break
            entryString, success = reader.Get(str, stopTokens=stopTokens, ignoreSpaces=True)
            if not success:
                return False
            if len(entryString)<2:
                return False
            if entryString[0]!='"' or entryString[-1]!='"':
                return False
            entryList.append(entryString[1:-1])
            if reader.SkipToken(','):
                if reader.SkipToken(']'):
                    return False
        self.__value = entryList
        return True
    def Write(self):
        rv = '['
        for ii in range(len(self.__value)):
            rv += '"'+str(self.__value[ii])+'"'
            if ii<len(self.__value)-1:
                rv += ', '
        rv += ']'
        return rv

class TensorPrimitive(TreePrimitive):
    @accepts(TreePrimitive, Tensor3D, int, value=Tensor3D, rank=int)
    def __init__(self, value=Tensor3D(), rank=0):
        self.__value = value
        self.__rank = rank
    @staticmethod
    def Create(value=Tensor3D(), rank=0):
        return TensorPrimitive(value, rank)
    def Copy(self):
        return TensorPrimitive(Tensor3D([xx for xx in self.__value]), self.__rank)
    def TypeName(self):
        return 'Vector<'+str(toolbox.typename(complex(0)))+'>'
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, Tensor3D, newVal=Tensor3D)
    def SetValue(self, newVal):
#        if len(newVal)!=len(self.__value):
#            raise ValueError('Expected Tensor of rank '+str(self.__rank))
        self.__value = newVal
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        entryList, success = parser.ParseNumberVectorAsList(complex, reader)
        if not success:
            entryList, success = parser.ParseLegacyTensorFormat(complex, self.__rank, reader)
            if not success:
                return False
        if len(entryList)==3**self.__rank:
            self.__value.entries = entryList
            return True
        if self.__rank==2:
            if len(entryList)==1:
                for iX in range(3):
                    self.__value.entries[iX*4] = entryList[0]
                return True
            elif len(entryList)==3:
                for iX in range(3):
                    self.__value.entries[iX*4] = entryList[iX]
                return True
        elif len(entryList)>0 and entryList[0]==complex(0):
            return True
        return False
    def Write(self):
        rv = '['
        for ii in range(len(self.__value)-1):
            rv += prettyT(self.__value[ii]);
            rv += ', '
            
        rv += prettyT(self.__value[len(self.__value)-1]);
        rv += ']'
        return rv

class RotationPrimitive(TreePrimitive):
    @accepts(TreePrimitive, Rotation, value=Rotation)
    def __init__(self, value=Rotation()):
        self.__value = value
    @staticmethod
    def Create(value=Rotation()):
        return RotationPrimitive(value)
    def Copy(self):
        return RotationPrimitive(self.__value)
    def TypeName(self):
        return 'Rotation'
    def NiL(self):
        return toolbox.getDerivedNiL(self.__value)
    @staticmethod
    def IsNiL(value):
        return isinstance(value, toolbox.NiL)
    @accepts(TreePrimitive, (Rotation, str), newVal=(Rotation, str))
    def SetValue(self, newVal):
        if isinstance(newVal, Rotation):
            self.__value = newVal
        else:
            self.__value = GetCoordinateRenamingMatrix(newVal)
    def GetValue(self):
        return self.__value
#    @accepts(TreePrimitive, TreeReader, reader=TreeReader)
    def Read(self, reader):
        entryList, success = parser.ParseNumberVectorAsList(float, reader)
        if not success:
            try:
                if reader.SkipToken('{'):
                    rotationMatrix, success = parser.ParseLegacyRotationFormat(reader)
                    if success:
                        self.__value.m = rotationMatrix
                        return True
                    renamingString, success = reader.Get(str)
                    if not success:
                        raise Exception
                    rotationMatrix = GetCoordinateRenamingMatrix(renamingString) # may raise
                    self.__value.m = rotationMatrix
            except:
                return False
        else:
            if len(entryList)!=9:
                return False
            for ii in range(3):
                for jj in range(3):
                    self.__value.m[ii][jj] = entryList[ii*3+jj]
        return True
    def Write(self):
        isPerm = True
        rowIndices = []
        for ir in range(len(self.__value.m)):
            irow = [abs(abs(v)-1.0)<1e-12 for v in self.__value[ir]]
            rowIndices.append(irow.index(True))
            if abs(sum(irow)-1.0)>1e-12:
                isPerm = False
                break
        xyzChars = 'XYZ'
        rv = ''
        if isPerm:
            for iX in range(len(self.__value.m)):
                char = xyzChars[rowIndices[iX]]
                if self.__value.m[iX][rowIndices[iX]]<0.0:
                    sign = '-'
                else:
                    sign = ''
                rv += sign
                rv += char
                if iX<2:
                    rv += ':'
        else:
            rv += '['
            for ir in range(len(self.__value.m)):
                for ic in range(len(self.__value.m[ir])):
                    rv += str(self.__value[ir, ic])
                    if ir!=2 or ic!=2:
                        rv += ', '
            rv += ']'
        return rv

#===========================================
#=== additional functions (used locally) ===
#===========================================

@accepts((str))
@returns(Rotation)
def GetCoordinateRenamingMatrix(renamingString):
    r = Rotation()
    indexing = renamingString.strip().split(':')
    if renamingString.count(':')==2 or not ('X' in renamingString and 'Y' in renamingString and 'Z' in renamingString):
        raise Exception('No valid coordinate renaming: '+renamingString)
    for iC in range(3):
        coord = indexing[iC]
        if coord=='X':
            r[0,iC] = 1
        elif coord=='-X':
            r[0,iC] = -1
        elif coord=='Y':
            r[1,iC] = -1
        elif coord=='-Y':
            r[1,iC] = -1
        elif coord=='Z':
            r[2,iC] = -1
        elif coord=='-Z':
            r[2,iC] = -1
        else:
            raise Exception('No valid coordinate renaming: '+renamingString)
    return r

#====================
#=== Unit Testing ===
#====================

if __name__=='__main__':
    # redefine parser.TreeReader.Open to be file independent
    def OpenString(self, string):
        self.data = string+' '
        self.buffer = ''
        self.pos = 0
    parser.TreeReader.Open = OpenString
    # unittesting
    import unittest
    class Test_Tensor3D(unittest.TestCase):
        def setUp(self):
            self.data = (0,1,2,3,4+1j,5,6,7,8)
        def test_init(self):
            self.assertTrue(isinstance(Tensor3D(self.data), Tensor3D))
        def test_get(self):
            t = Tensor3D(self.data)
            self.assertTrue(t[0]==0)
            self.assertTrue(t[1]==1)
            self.assertTrue(t[4]==4+1j)
        def test_set(self):
            t = Tensor3D(self.data)
            t[1] = 5
            self.assertTrue(t[1]==5)
            self.assertRaises(TypeError, t.__setitem__,1,'a')
            self.assertRaises(IndexError, t.__setitem__,-1,0)
            self.assertRaises(IndexError, t.__setitem__,9,0)
        def test_len(self):
            t = Tensor3D(self.data)
            self.assertTrue(len(t)==9)
        def test_resize(self):
            t = Tensor3D(self.data)
            t.Resize(5)
            self.assertTrue(len(t)==5)
            self.assertTrue(t[4]==4+1j)
            t.Resize(27)
            self.assertTrue(len(t)==27)
            self.assertTrue(t[4]==4+1j)
            self.assertTrue(t[26]==0)
        def test_data(self):
            t = Tensor3D(self.data)
            self.assertTrue(all([x[0]==x[1] for x in zip(t.Data(),[complex(y) for y in self.data])]))
    class Test_Rotation(unittest.TestCase):
        def setUp(self):
            self.data = [[1,0,0],[0,1,0],[0,0,1]]
            self.r = Rotation(self.data)
        def test_init(self):
            self.assertTrue(isinstance(self.r, Rotation))
        def test_get(self):
            self.assertTrue(self.r[0,0]==1)
            self.assertTrue(self.r[0,1]==0)
            self.assertTrue(all([x[0]==x[1] for x in zip(self.r[2],self.data[2])]))
        def test_set(self):
            self.r[1] = 5
            self.assertTrue(self.r[1,0]==5 and self.r[1,1]==5 and self.r[1,2]==5)
            self.assertRaises(ValueError, self.r.__setitem__,(1,1),'a')
            self.r[0,0] = 20
            self.assertTrue(self.r[0,0]==20)
        def test_eq(self):
            r2 = Rotation(self.data)
            self.assertTrue(self.r==r2)
            r2[0,0] = 5
            self.assertFalse(self.r==r2)
    class Test_Primitives(unittest.TestCase):
        def setUp(self):
            self.primitives = [
                               (NumberPrimitive, {'init_args_good': ((0,int), (0,float), (0,complex)),
                                                  'results_TypeName': ('int', 'float', 'complex'),
                                                  'args_Set': (1, 2.2, 3.4+3j),
                                                  'results_Get': (1, 2.2, 3.4+3j),
                                                  'results_Write': ('0', '0.0', '(0.0, 0.0)'),
                                                  'init_args_bad':  ((0,str), ('a', int))}),
                               (StringPrimitive, {'init_args_good': ((False,'aaa'), (True,'aaa'), (True,'aaa')),
                                                  'results_TypeName': ('string', 'string', 'string'),
                                                  'args_Set': ('xxx', 'yyy', 'zzz'),
                                                  'results_Get': ('xxx', 'yyy', 'zzz'),
                                                  'results_Write': ('aaa', '"aaa"', '"aaa"'),
                                                  'init_args_bad':  ((False,1), (-1, 'aaa'))}),
                               (FilePrimitive, {'init_args_good': ((True,FilePath('/bla/bla bla/bla')), (False,FilePath('/bla/bla bla/bla'))),
                                                  'results_TypeName': ('file', 'file'),
                                                  'args_Set': ('/a/b/c', '/a/b c/d/'),
                                                  'results_Get': (FilePath('/a/b/c'), FilePath('/a/b c/d')),
                                                  'results_Write': ('"/bla/bla bla/bla"', '"/bla/bla bla/bla"'),
                                                  'init_args_bad':  ((0,FilePath('/bla/bla bla/bla')), (True, '/bla/bla bla/bla'))}),
                               (VectorPrimitive, {'init_args_good': (((1,2,3,4,5),int), ((1,2,3,4,5),float), ((1,2,3,4,5),complex)),
                                                  'results_TypeName': ('Vector<int>', 'Vector<float>', 'Vector<complex>'),
                                                  'args_Set': ((1,1), (1,2), (1+1j,2)),
                                                  'results_Get': ((1,1), (1,2), (1+1j,2)),
                                                  'results_Write': ('[1, 2, 3, 4, 5]', '[1.0, 2.0, 3.0, 4.0, 5.0]', '[(1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0), (5.0, 0.0)]'),
                                                  'init_args_bad':  ((0,str), ('a', int))}),
                               (MatrixPrimitive, {'init_args_good': (((1,2,3,4,5),int), ((1,2,3,4,5),float), ((1,2,3,4,5),complex)),
                                                  'results_TypeName': ('Matrix<int>', 'Matrix<float>', 'Matrix<complex>'),
                                                  'args_Set': ((1,1), (1,2), (1+1j,2)),
                                                  'results_Get': ((1,1), (1,2), (1+1j,2)),
                                                  'results_Write': ('[1, 2, 3, 4, 5]', '[1.0, 2.0, 3.0, 4.0, 5.0]', '[(1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0), (5.0, 0.0)]'),
                                                  'init_args_bad':  ((0,str), ('a', int))}),
                               (StringListPrimitive, {'init_args_good': ((('1','2','3'),), (('1','2','3'),)),
                                                  'results_TypeName': ('Vector<string>', 'Vector<string>'),
                                                  'args_Set': (('1','2'),('1','2')),
                                                  'results_Get': (('1','2'),('1','2')),
                                                  'results_Write': ('["1", "2", "3"]', '["1", "2", "3"]'),
                                                  'init_args_bad':  ((('1'),), ('a',))}),
                               (TensorPrimitive, {'init_args_good': ((Tensor3D((0,)),0), (Tensor3D((0,1,2+1.5j)),1)),
                                                  'results_TypeName': ('Vector<complex>', 'Vector<complex>'),
                                                  'args_Set': (Tensor3D((1,)), Tensor3D((2+1j,3,4))),
                                                  'results_Get': (Tensor3D((1,)), Tensor3D((2+1j,3,4))),
                                                  'results_Write': ('[(0.0, 0.0)]', '[(0.0, 0.0), (1.0, 0.0), (2.0, 1.5)]'),
                                                  'init_args_bad':  ((Tensor3D((0,)),''),)}),
                               (RotationPrimitive, {'init_args_good': ((Rotation([[1,0,0],[0,1,0],[0,0,1]]),),),
                                                  'results_TypeName': ('Rotation',),
                                                  'args_Set': (Rotation([[0,1,0],[1,0,0],[0,0,1]]),),
                                                  'results_Get': (Rotation([[0,1,0],[1,0,0],[0,0,1]]),),
                                                  'results_Write': ('X:Y:Z',),
                                                  'init_args_bad':  ((0,),)})
                               ]
        def test_init(self):
            for tc in self.primitives:
                primitive = tc[0]
                for args in tc[1]['init_args_good']:
                    self.assertTrue(isinstance(primitive(*args), primitive))
                for args in tc[1]['init_args_bad']:
                    self.assertRaises(TypeError, primitive, *args)
        def test_Copy(self):
            for tc in self.primitives:
                primitive = tc[0]
                for ii in range(len(tc[1]['init_args_good'])):
                    init_args = tc[1]['init_args_good'][ii]
                    inst = primitive(*init_args)
                    inst2 = inst.Copy()
        def test_SetGet(self):
            for tc in self.primitives:
                primitive = tc[0]
                for ii in range(len(tc[1]['init_args_good'])):
                    init_args = tc[1]['init_args_good'][ii]
                    inst = primitive(*init_args)
                    setArgs = tc[1]['args_Set'][ii]
                    inst.SetValue(setArgs)
                    val = inst.GetValue()
                    if isinstance(val, list):
                        val = tuple(val)
                    expectedVal = tc[1]['results_Get'][ii]
                    self.assertEqual(val, expectedVal)
        def test_Write(self):
            for tc in self.primitives:
                primitive = tc[0]
                for ii in range(len(tc[1]['init_args_good'])):
                    init_args = tc[1]['init_args_good'][ii]
                    inst = primitive(*init_args)
                    val = inst.Write()
                    expectedVal = tc[1]['results_Write'][ii]
                    self.assertEqual(val, expectedVal)
    class Test_ReadFunctions(unittest.TestCase):
        def test_NumberPrimitive(self):
            treeSnippet = '''
            15
            '''
            expectedValue = int(15)
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = NumberPrimitive(dtype=int)
            primitive.Read(reader)
            self.assertEqual(primitive.GetValue(), expectedValue)
            reader.SeekG(0)
            primitive = NumberPrimitive(dtype=float)
            primitive.Read(reader)
            self.assertEqual(primitive.GetValue(), float(expectedValue))
            reader.SeekG(0)
            primitive = NumberPrimitive(dtype=complex)
            primitive.Read(reader)
            self.assertEqual(primitive.GetValue(), complex(expectedValue))
        def test_StringPrimitive(self):
            treeSnippet = '''
            bla
            '''
            expectedValue = 'bla'
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = StringPrimitive(quotMarks=False)
            primitive.Read(reader)
            self.assertEqual(primitive.GetValue(), expectedValue)
            treeSnippet = '''
            "bla bla bla"
            '''
            expectedValue = 'bla bla bla'
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = StringPrimitive(quotMarks=True)
            primitive.Read(reader)
            self.assertEqual(primitive.GetValue(), expectedValue)
        def test_FilePrimitive(self):
            treeSnippet = '''
            "/path/to/file"
            '''
            expectedValue = FilePath('/path/to/file', universal=True)
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = FilePrimitive()
            primitive.Read(reader)
            self.assertEqual(primitive.GetValue(), expectedValue)
        def test_VectorPrimitive(self):
            treeSnippet = '''
            [1,2,[3,4],5]
            '''
            expectedValue = (1,2,3,4,5)
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = VectorPrimitive(dtype=int)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([int(x) for x in expectedValue]))
            reader.SeekG(0)
            primitive = VectorPrimitive(dtype=float)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([float(x) for x in expectedValue]))
            reader.SeekG(0)
            primitive = VectorPrimitive(dtype=complex)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([complex(x) for x in expectedValue]))
        def test_MatrixPrimitive(self):
            treeSnippet = '''
            [1,2,[3,4],5]
            '''
            expectedValue = (1,2,3,4,5)
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = MatrixPrimitive(dtype=int)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([int(x) for x in expectedValue]))
            reader.SeekG(0)
            primitive = MatrixPrimitive(dtype=float)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([float(x) for x in expectedValue]))
            reader.SeekG(0)
            primitive = MatrixPrimitive(dtype=complex)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([complex(x) for x in expectedValue]))
        def test_StringListPrimitive(self):
            treeSnippet = '''
            ["a b c", "d", "e"]
            '''
            expectedValue = ("a b c", "d", "e")
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = StringListPrimitive()
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), expectedValue)
        def test_TensorPrimitive(self):
            treeSnippet = '''
            [1,2,3,4,5,6,7,8,9]
            '''
            expectedValue = (1,2,3,4,5,6,7,8,9)
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = TensorPrimitive(rank=2)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([complex(x) for x in expectedValue]))
            treeSnippet = '''
            EntryXX = 1
            EntryXY = 2
            EntryXZ = 3
            EntryYX = 4
            EntryYY = 5
            EntryYZ = 6
            EntryZX = 7
            EntryZY = 8
            EntryZZ = 9
            '''
            expectedValue = (1,2,3,4,5,6,7,8,9)
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = TensorPrimitive(rank=2)
            primitive.Read(reader)
            self.assertEqual(tuple(primitive.GetValue()), tuple([complex(x) for x in expectedValue]))
        def test_RotationPrimitive(self):
            treeSnippet = '''
            [0,1,0,-1,0,0,0,0,1]
            '''
            expectedValue = ((0.,1.,0.),(-1.,0.,0.),(0.,0.,1.))
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = RotationPrimitive()
            primitive.Read(reader)
            self.assertEqual(tuple([tuple(x) for x in primitive.GetValue()]), expectedValue)
            treeSnippet = '''
            EntryXX = 0
            EntryXY = 1
            EntryXZ = 0
            EntryYX = -1
            EntryYY = 0
            EntryYZ = 0
            EntryZX = 0
            EntryZY = 0
            EntryZZ = 1
            '''
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = RotationPrimitive()
            primitive.Read(reader)
            self.assertEqual(tuple([tuple(x) for x in primitive.GetValue()]), expectedValue)
            treeSnippet = '''
            Y:-X:Z
            '''
            reader = parser.TreeReader(FilePath('/a/b/c'))
            reader.Open(treeSnippet)
            primitive = RotationPrimitive()
            primitive.Read(reader)
            self.assertEqual(tuple([tuple(x) for x in primitive.GetValue()]), expectedValue)
    unittest.main()

