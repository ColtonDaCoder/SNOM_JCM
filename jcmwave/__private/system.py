'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

import os
from .decorators import accepts
from .toolbox import AsciiVector
#from builtins import str

class FilePath(AsciiVector):
    @accepts(object, (str), bool, data=(str), universal=bool)
    def __init__(self, data='.', universal=False):
        self._delimiter = os.sep
        self._data = []
        delimiters = set()
        delimiters.add(self._delimiter)
        if universal:
            delimiters.add('\\')
            delimiters.add('/')
        self.Import(data, delimiters)
        self._data = [x for x in self._data if len(x)>0]
        if len(data)>0 and data.strip()[0]==self._delimiter:
            self._isAbsolute = True
        else:
            self._isAbsolute = False
    def Copy(self):
        cp = FilePath(data=self.Path())
        return cp
    def File(self):
        return self.FileName()
    def Dir(self):
        return self.DirName()
    def Path(self):
        return self.Export()
    def FileName(self):
        return self.At(-1)
    def DirName(self):
        return self.ExportParent()+self._delimiter
    def BaseName(self):
        return self.At(-1).split('.')[0]
    def CompleteSuffix(self):
        return '.'.join(self.At(-1).split('.')[1:])
    def IsAbsolute(self):
        return self._isAbsolute
    def SetAbsolute(self):
        self._isAbsolute = True
    def SetRelative(self):
        self._isAbsolute = False
    def Export(self):
        rv = self._delimiter.join(self._data)
        if self._isAbsolute:
            rv = self._delimiter+rv
        return rv
    def ExportParent(self):
        rv = self._delimiter.join(self._data[:-1])
        if self._isAbsolute:
            rv = self._delimiter+rv
        return rv
    def __eq__(self, other):
        if isinstance(other, FilePath) and self._isAbsolute!=other._isAbsolute:
            return False
        else:
            return AsciiVector.__eq__(self, other)
    def __ne__(self, other):
        return (not self.__eq__(other))


if __name__=='__main__':
    import unittest
    class Test_FilePath(unittest.TestCase):
        def test_FilePath_init(self):
            dataString = '/usr/bin/file.exe'
            dataInt = 7
            self.assertTrue(isinstance(FilePath(dataString), FilePath))
            self.assertTrue(isinstance(FilePath(str(dataString)), FilePath))
        def test_FilePath_File(self):
            dataString = '/usr/bin/file.exe'
            fp = FilePath(dataString)
            self.assertEqual(fp.File(), 'file.exe')
        def test_FilePath_Dir(self):
            dataString = '/usr/bin/file.exe'
            fp = FilePath(dataString)
            self.assertEqual(fp.Dir(), '/usr/bin/')
        def test_FilePath_Path(self):
            dataString = '/usr/bin/file.exe'
            fp = FilePath(dataString)
            self.assertEqual(fp.Path(), dataString)
        def test_FilePath_BaseName(self):
            dataString = '/usr/bin/file.exe.exe2'
            fp = FilePath(dataString)
            self.assertEqual(fp.BaseName(), 'file')
        def test_FilePath_CompleteSuffix(self):
            dataString = '/usr/bin/file.exe.exe2'
            fp = FilePath(dataString)
            self.assertEqual(fp.CompleteSuffix(), 'exe.exe2')
    unittest.main()
