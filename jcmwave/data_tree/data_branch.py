'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

import os
import weakref
#import jcmwave.data_tree.data_primitives as  data_primitives
from jcmwave.__private.decorators import accepts
from jcmwave.__private.toolbox import AsciiVector
from jcmwave.__private.system import FilePath

TREE_PATH_TEMPLATE = AsciiVector(delimiter=':')

DEAD_WEAK_REF = weakref.ref(FilePath()) # create a dead weak reference (returns None at call)

class TreeDir:
    import jcmwave.data_tree.data_primitives as  data_primitives
    def __init__(self, dirName='', father=None, branchDir=None):
        if branchDir!=None:
            self.dirs = branchDir.dirs.copy()
            self.primitives = {}
            for vIter in branchDir.primitives.items():
                self.primitives[vIter[0]] = vIter[1].Copy()
            self.name = branchDir.GetName()
            self.trunkDir = branchDir.trunkDir
            self.sourceDir = branchDir.sourceDir.Copy()
        else:
            self.dirs = {}
            self.primitives = {}
            self.name = dirName
            self.trunkDir = ''
            self.sourceDir = FilePath()
            self.dummyDirs = [] # stack of strings
        if father is None:
            self.father = DEAD_WEAK_REF
        else:
            self.father = weakref.ref(father)
            self.father().AddTreeDir(self)
        self.alias = ''
    @staticmethod
    def Create(dirName=None, father=None, branchDir=None):
        return TreeDir(dirName, father, branchDir)
    def Copy(self):
        cp = TreeDir()
        cp.dirs = self.dirs.copy()
        cp.primitives = {}
        for vIter in self.primitives.items():
            cp.primitives[vIter[0]] = vIter[1].Copy()
        cp.name = self.name
        cp.trunkDir = self.trunkDir
        cp.sourceDir = self.sourceDir.Copy()
        cp.alias = self.alias
        cp.dummyDirs = [x for x in self.dummyDirs]
        return cp
    def GetName(self):
        return self.name
    def GetFullName(self):
        path = TREE_PATH_TEMPLATE.Copy()
        if self.father()!=None:
            path.PushBack(self.father().GetFullName())
        path.PushBack(self.GetName())
        return path.Export()
    def SetAlias(self, alias=''):
        self.alias = str(alias)
    def Alias(self):
        return self.alias
    def Get(self, itemname='', multipleindex=0):
        return self.GetPrimitive(itemname, multipleindex)
    def TryGet(self, fallback=None, itemname='', multipleindex=0):
        if self.GetPrimitive(itemname, multipleindex) is None:
            return fallback
        else:
            return self.GetPrimitive(itemname, multipleindex)
    def GetPrimitive(self, itemname, multipleindex=0):
        key = (itemname, multipleindex)
        if key in self.primitives:
            return self.primitives[key]
        else:
            return None
    def GetPrimitives(self):
        return self.primitives.copy()
    def GetDir(self, itemname, multipleindex=0):
        key = (itemname, multipleindex)
        if key in self.dirs:
            return self.dirs[key]
        else:
            return None
    def GetDirs(self):
        return self.dirs.copy()
    def AddPrimitive(self, itemname='', newitem=None):
        if newitem==None:
            return None
        multipleindex = 0
        key = (itemname, multipleindex)
        while key in self.primitives:
            multipleindex += 1
            key = (itemname, multipleindex)
        self.primitives[key] = newitem
        return newitem
    def SetPrimitive(self, itemname='', newitem=None, multipleindex = 0):
        if newitem==None: return None
        key = (itemname, multipleindex)
        self.primitives[key] = newitem
        return newitem
    def AddTreeDir(self, newItem=None):
        if newItem is None:
            return
        itemname = newItem.GetName()
        multipleindex = 0
        key = (itemname, multipleindex)
        while key in self.dirs:
            multipleindex += 1
            key = (itemname, multipleindex)
        newItem.father = weakref.ref(self)
        self.dirs[key] = newItem
        return newItem
    def Add(self, itemname=None, item=None):
        # @TODO: check (this does not seem to work correctly)
        if isinstance(item, data_primitives.TreePrimitive):
            if not isinstance(itemname, str):
                return None
            return self.AddPrimitive(itemname, item)
        elif isinstance(item, TreeDir):
            return self.AddTreeDir(item)
        else:
            return None
    def ReleaseDir(self, itemname='', multipleindex=0):
        key = (itemname, multipleindex)
        return self.dirs.pop(key, None)
    def ReleasePrimitive(self, itemname='', multipleindex=0):
        key = (itemname, multipleindex)
        return self.primitives.pop(key, None)
    def GetFather(self):
        return self.father()
    def GetTrunkDir(self):
        return self.GetDir(self.trunkDir)
    def SetTrunkDir(self, trunkDir=''):
        self.trunkDir = trunkDir
    def FinalDir(self):
        d = self
        while d.GetTrunkDir()!=None:
            d = d.GetTrunkDir()
        return d
    @accepts(object, FilePath, sourceFile=FilePath)
    def SetSourceFile(self, sourceFile):
        self.sourceDir = sourceFile
    def GetSourceFile(self):
        return self.sourceDir
    @accepts(object, (str), dummyDir=(str))
    def AddDummyDir(self, dummyDir):
        if not dummyDir in self.dummyDirs:
            self.dummyDirs.append(dummyDir)
        return dummyDir
    def DummyDirs(self):
        return [x for x in self.dummyDirs]
    @staticmethod
    def __ExpandFilePaths(treeDir, sourceDirPath):
        sourceDirPathString = os.path.normpath(sourceDirPath.Export())+os.sep
        for primitive in treeDir.primitives.values():
            if isinstance(primitive, data_primitives.FilePrimitive):
                relPath = primitive.GetValue()
                relPathString = os.path.normpath(relPath.Export())
                absPathString = os.path.abspath(sourceDirPathString+relPathString)
                relPath.Import(absPathString)
        for td in list(treeDir.dirs.values()):
            TreeDir.__ExpandFilePaths(td, sourceDirPath)

class TreeAdaptor:
    def __init__(self):
        pass
    def Transform(self, treeDir):
        raise Exception('Missing implementation.')

def Copy(sourceTreeDir,
         itemString,
         targetTreeDir,
         itemString_=''):
    if len(itemString_)==0:
        itemString_ = itemString
    if sourceTreeDir.GetPrimitive(itemString)!=None:
        targetTreeDir.AddPrimitive(itemString_, sourceTreeDir.GetPrimitive(itemString).Copy())
    if sourceTreeDir.GetDir(itemString)!=None:
        targetTreeDir.AddDir(itemString_, sourceTreeDir.GetDir(itemString).Copy())
        if sourceTreeDir.GetTrunkDir()==sourceTreeDir.GetDir(itemString):
            targetTreeDir.SetTrunkDir(itemString_)

def CD(currentTreeDir, itemString):
    if currentTreeDir is None:
        dir_ = None
    elif itemString=='.':
        dir_ = currentTreeDir
    elif itemString=='..':
        dir_ = currentTreeDir.GetFather()
    else:
        dir_ = currentTreeDir.GetDir(itemString)
    if dir_ is None:
        success = False
    else:
        success = True
    return dir_, success

def MKDir(currentTreeDir, itemString):
    if currentTreeDir is None:
        return None
    else:
        return TreeDir.Create(father=currentTreeDir, dirName=itemString)

def GetFinalDir(currentTreeDir, 
                prototypeDirSchema):
    while prototypeDirSchema!=None and currentTreeDir.GetTrunkDir()!=None:
        currentTreeDir = currentTreeDir.GetTrunkDir()
        prototypeDirSchema = prototypeDirSchema.GetChoiceDir(currentTreeDir.GetName())
    return prototypeDirSchema

if __name__=='__main__':
    import unittest
    class Test_TreeDir(unittest.TestCase):
        def setUp(self):
            self.db1 = TreeDir.Create('db1')
            self.db2 = TreeDir.Create('db2', father=self.db1)
        def test_Add_and_Get_Primitive_and_TreeDir(self):
            tp = data_primitives.FilePrimitive()
            td = TreeDir.Create('td')
            self.db1.Add('tp', tp)
            self.db1.Add(None, td)
            self.assertEqual(tp, self.db1.GetPrimitive('tp'))
            self.assertEqual(tp, self.db1.Get('tp'))
            self.assertEqual(td, self.db1.GetDir('td'))
        def test_Add_and_Get_DummyDir(self):
            self.db1.AddDummyDir('DummyDir')
            self.assertTrue('DummyDir' in self.db1.DummyDirs())
        def test_Set_and_Get_Alias(self):
            self.db1.SetAlias('ali')
            self.assertEqual(self.db1.Alias(), 'ali')
        def test_Copy_with_SourceFile_TrunkDir(self):
            self.db2.SetAlias('ali')
            tp = data_primitives.FilePrimitive()
            td = TreeDir.Create('td')
            self.db2.Add('tp', tp)
            self.db2.Add(None, td)
            self.db2.SetSourceFile(FilePath('/path/to/sourcefile'))
            self.db2.AddDummyDir('DummyDir')
            self.db2.SetTrunkDir('td')
            cp = self.db2.Copy()
            self.assertEqual(cp.GetTrunkDir(), self.db2.GetTrunkDir())
            self.assertEqual(cp.GetSourceFile(), self.db2.GetSourceFile())
            self.assertTrue('DummyDir' in cp.DummyDirs())
        def test_FinalDir(self):
            td = TreeDir.Create('td')
            self.db2.Add(None, td)
            self.db2.SetTrunkDir('td')
            td2 = TreeDir.Create('td2')
            td.Add(None, td2)
            td.SetTrunkDir('td2')
            self.assertEqual(self.db2.FinalDir(), td2)
        def test_GetDirs(self):
            td1 = TreeDir.Create('td1')
            td2 = TreeDir.Create('td2')
            self.db2.Add(None, td1)
            self.db2.Add(None, td2)
            dirs = self.db2.GetDirs()
            for d in (td1,td2):
                self.assertTrue(d in dirs.values())
        def test_GetFather(self):
            self.assertEqual(self.db2.GetFather(), self.db1)
        def test_GetFullName(self):
            fn2 = self.db2.GetFullName()
            self.assertEqual('db1:db2', fn2)
        def test_GetName(self):
            self.assertEqual('db1', self.db1.GetName())
            self.assertEqual('db2', self.db2.GetName())
        def test_GetPrimitives(self):
            tp = data_primitives.FilePrimitive()
            self.db2.Add('tp', tp)
            self.assertTrue(tp in self.db2.GetPrimitives().values())
        def test_ReleaseDir(self):
            self.db1.ReleaseDir('db2')
            self.assertFalse(self.db2 in self.db1.GetDirs().values())
        def test_ReleasePrimitive(self):
            tp = data_primitives.FilePrimitive()
            self.db2.Add('tp', tp)
            self.db2.ReleasePrimitive('tp')
            self.assertFalse(tp in self.db2.GetPrimitives().values())
        def test_TryGet(self):
            tp = data_primitives.FilePrimitive()
            self.db2.Add('tp', tp)
            self.assertEqual(self.db2.TryGet('fb', 'tp'), tp)
            self.assertEqual(self.db2.TryGet('fb', 'tp2'), 'fb')
    class Test_CD(unittest.TestCase):
        def setUp(self):
            self.db1 = TreeDir.Create('db1')
            self.db2 = TreeDir.Create('db2', father=self.db1)
        def test_SameDir(self):
            self.assertEqual(CD(self.db1, '.')[0], self.db1)
        def test_ParentDir(self):
            self.assertEqual(CD(self.db2, '..')[0], self.db1)
        def test_SubDir(self):
            self.assertEqual(CD(self.db1, 'db2')[0], self.db2)
    class Test_MKDir(unittest.TestCase):
        def setUp(self):
            self.db1 = TreeDir.Create('db1')
            self.db2 = TreeDir.Create('db2', father=self.db1)
        def test_SameDir(self):
            dir3 = MKDir(self.db1, 'dir3')
            self.assertEqual(dir3.GetFather(), self.db1)
    class Test_GetFinalDir(unittest.TestCase):
        def setUp(self):
            pass # not implemented
    unittest.main()
