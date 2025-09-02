'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

from jcmwave.__private.toolbox import AsciiVector
import jcmwave.data_tree.schema_primitives as schema_primitives

TREE_PATH_TEMPLATE = AsciiVector(delimiter=':')

class DirSchema:
    def __init__(self, name='', aliasNames=set()):
        self._name = str(name)
        self._aliasNames = set(aliasNames).copy()
        self._dirs = {}
        self._primitives = {}
        self._choiceDirs = {}
        self._adaptors = {}
        self._thisAdaptors = set()
        self._defaultChoiceDir = ''
        self._aliases = {}
        self._multipleItems = set()
        self._dummyDirs = set()
        self._hiddenItems = set()
        self._obsoleteItems = set()
        self._optionalItems = set()
        self._exclusions = {}
        self._inclusions = {}
        self._shortCut = None
        self._father = None
        self._decoration = dict();
    @staticmethod
    def Create(father=None, name=None, aliasNames=None):
        if name is None:
            raise AttributeError('DirSchema::Create(...): zero-pointer name.')
        if aliasNames is None:
            aliasNames = set()
        newItem = DirSchema(name, aliasNames)
        if father!=None:
            newItem._father = father
            father.AddChoiceDir(newItem, False)
        return newItem
    def GetName(self):
        return self._name
    def GetAliasNames(self):
        return self._aliasNames.copy()
    def GetFullName(self):
        if self._father is None:
            path = TREE_PATH_TEMPLATE.Copy()
        else:
            path = self._father.GetFullName()
        path.PushBack(self.GetName())
        return path
    def GetPrimitive(self, itemName, iOverload=0):
        if (itemName, iOverload) in self._primitives:
            return self._primitives[(itemName, iOverload)]
        else:
            return None
    def GetPrimitiveOverloads(self, itemName):
       overloads = list()
       while True:
         p = self.GetPrimitive(itemName, len(overloads));
         if p==None: break;
         overloads.append(p);
       return overloads
    def GetDir(self, itemName):
        trueName = self.GetTrueName(itemName)
        if trueName in self._dirs:
            return self._dirs[trueName]
        elif itemName in self._dirs:
            return self._dirs[itemName]
        else:
            return None
    def GetChoiceDir(self, itemName):
        trueName = self.GetTrueName(itemName)
        if itemName in self._choiceDirs:
            return self._choiceDirs[itemName]
        elif trueName in self._choiceDirs:
            return self._choiceDirs[trueName]
        else:
            return None
    def DefaultChoiceDir(self):
        return self.GetChoiceDir(self._defaultChoiceDir)
    def GetFather(self):
        return self._father
    def SetFather(self, father):
        self._father = father
    def GetChoiceDirs(self):
        return [x for x in self._choiceDirs]
    def GetDirs(self):
        return self._dirs.copy()
    def GetThisAdaptors(self):
        return self._thisAdaptors
    def GetPrimitives(self):
        return self._primitives.copy()
    def AddPrimitive(self, itemName, newItem):
        #self.__AssureNonExistence(itemName)
        iOverload = 0
        while (itemName, iOverload) in self._primitives: iOverload+=1;
        self._primitives[(itemName, iOverload)] = newItem
    def AddDirSchema(self, newItem):
        itemName = newItem.GetName()
        #self.__AssureNonExistence(itemName)
        newItem.SetFather(self)
        adaptors = newItem.GetThisAdaptors()
        aliasNames = newItem.GetAliasNames()
        self._dirs[itemName] = newItem
        for ada in adaptors:
            self.AddSchemaAdaptor(ada)
        for alias in aliasNames:
            self.SetAlias(itemName, alias)
    def AddSchemaAdaptor(self, schemaAdaptor):
        #self.__AssureNonExistence(schemaAdaptor.schema.GetName())
        self._adaptors[schemaAdaptor.schema.GetName()] = schemaAdaptor
    def AddChoiceDir(self, choiceDir, setDefault=False):
        itemName = choiceDir.GetName()
        #self.__AssureNonExistence(itemName)
        choiceDir.SetFather(self)
        self._choiceDirs[itemName] = choiceDir
        if setDefault:
            self._defaultChoiceDir = itemName
    def Add(self, newItem, name=None):
        # @todo: untested, may not work
        if isinstance(item, schema_primitives.PrimitiveSchema):
            if not isinstance(name, str):
                return None
            return self.AddPrimitive(name, item)
        elif isinstance(item, DirSchema):
            return self.AddDirSchema(item)
        elif isinstance(item, SchemaAdaptor):
            return self.AddSchemaAdaptor(item)
        else:
            return None
    def SetDefaultChoiceDir(self, dirName):
        self._defaultChoiceDir = dirName
    def GetTrueName(self, aliasName):
        if aliasName in self._aliases:
            return self._aliases[aliasName]
        return aliasName
    def AddDummyDir(self, dirName):
        self._dummyDirs.add(dirName)
    def IsDummyDir(self, dirName):
        return (dirName in self._dummyDirs)
    def TagMultiple(self, itemName):
        self._multipleItems.add(itemName)
    def IsMultiple(self, itemName):
        return (itemName in self._multipleItems)
    def TagHidden(self, itemName):
        self._hiddenItems.add(itemName)
    def IsHidden(self, itemName):
        return (itemName in self._hiddenItems)
    def TagObsolete(self, itemName):
        self._obsoleteItems.add(itemName)
    def IsObsolete(self, itemName):
        return (itemName in self._obsoleteItems)
    def TagOptional(self, itemName):
        self._optionalItems.add(itemName)
    def IsOptional(self, itemName):
        return (itemName in self._optionalItems)
    def SetExclusion(self, itemName, excludedItemName):
        if itemName not in self._exclusions:
            self._exclusions[itemName] = set()
        self._exclusions[itemName].add(excludedItemName)
    def SetMutualExclusion(self, itemName1, itemName2):
        self.SetExclusion(itemName1, itemName2)
        self.SetExclusion(itemName2, itemName1)
    def GetExclusions(self, itemName):
        if itemName not in self._exclusions:
            return set()
        return self._exclusions[itemName]
    def SetInclusion(self, itemName, includedItemName):
        if itemName not in self._inclusions:
            self._inclusions[itemName] = set()
        self._inclusions[itemName].add(includedItemName)
    def SetMutualInclusion(self, itemName1, itemName2):
        self.SetInclusion(itemName1, itemName2)
        self.SetInclusion(itemName2, itemName1)
    def GetInclusions(self, itemName):
        if itemName not in self._inclusions:
            return set()
        return self._inclusions[itemName]
    def SetAlias(self, itemName, alias):
        trueName = self.GetTrueName(itemName)
        if (self.GetDir(trueName)!=None or
            self.GetChoiceDir(trueName)!=None or
            self.GetPrimitive(trueName)!=None):
            self._aliases[alias] = trueName
    def GetShortCut(self):
        return self._shortCut
    def SetShortCut(self, shortCut):
        self._shortCut = shortCut
    def GetAdaptor(self, itemName):
        if itemName in self._adaptors:
            return self._adaptors[itemName]
        else:
            return None
    def __AssureNonExistence(self, itemName):
        trueName = self.GetTrueName(itemName)
        if ((trueName, 0) in self._primitives or
            trueName in self._dirs or
            trueName in self._adaptors):
            raise ValueError('Schema::Add(...): Item already exists.')

    def GetDecoration(self):
        return self._decoration;
class SchemaAdaptor:
    def __init__(self):
        schema = None
        treeAdaptors = {}

def PrintPrototypeDirContent(fileObj,
                            dirRoot,
                            showHiddenEntries=False,
                            indentation=0):
    if dirRoot is None:
        return
    

def GetInputSchema():
    pass

if __name__=='__main__':
    import unittest
    from . import schema_primitives
    class Test_DirSchema(unittest.TestCase):
        def setUp(self):
            self.dir1 = DirSchema.Create(None, 'dir1', ('Dir1','directory1'))
            self.dir2 = DirSchema.Create(self.dir1, 'dir2', ('Dir2','directory2'))
        def test_SetFather(self):
            pass
        def test_AddChoiceDir(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddChoiceDir(cd)
            cd2 = DirSchema.Create(None, 'cd2')
            self.dir1.AddChoiceDir(cd2, True)
        def test_GetChoiceDir(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddChoiceDir(cd)
            cdObject = self.dir1.GetChoiceDir('cd')
            self.assertEqual(cdObject,cd)
        def test_DefaultChoiceDir(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddChoiceDir(cd)
            cd2 = DirSchema.Create(None, 'cd2')
            self.dir1.AddChoiceDir(cd2, True)
            defCD = self.dir1.DefaultChoiceDir()
            self.assertEqual(defCD, cd2)
        def test_GetChoiceDirs(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddChoiceDir(cd)
            cd2 = DirSchema.Create(None, 'cd2')
            self.dir1.AddChoiceDir(cd2, True)
            for c in ('cd','cd2'):
                self.assertTrue(c in self.dir1.GetChoiceDirs())
        def test_SetDefaultChoiceDir(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddChoiceDir(cd)
            cd2 = DirSchema.Create(None, 'cd2')
            self.dir1.AddChoiceDir(cd2, True)
            self.dir1.SetDefaultChoiceDir('cd')
            self.assertEqual(cd, self.dir1.DefaultChoiceDir())
        def test_AddDirSchema(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddDirSchema(cd)
            self.assertEqual(self.dir1.GetDir('cd'), cd)
        def test_DummyDir_Methods(self):
            self.dir1.AddDummyDir('bla')
            self.assertTrue(self.dir1.IsDummyDir('bla'))
        def test_Primitive_Methods(self):
            sp = schema_primitives.RotationSchema()
            self.dir1.AddPrimitive('rot1', sp)
            self.assertEqual(self.dir1.GetPrimitive('rot1'), sp)
            self.assertTrue(sp in list(self.dir1.GetPrimitives().values()))
        def test_SchemaAdaptor_Methods(self):
            cd = DirSchema.Create(None, 'cd')
            schemaAdaptor = SchemaAdaptor()
            schemaAdaptor.schema = cd
            self.dir1.AddSchemaAdaptor(schemaAdaptor)
            self.assertEqual(self.dir1.GetAdaptor('cd'), schemaAdaptor)
        def test_Alias_Methods(self):
            sp = schema_primitives.RotationSchema()
            self.dir1.AddPrimitive('rot1', sp)
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddChoiceDir(cd)
            self.dir1.SetAlias('rot1', 'rot2')
            self.dir1.SetAlias('cd', 'cd2')
            self.assertEqual(self.dir1.GetTrueName('cd2'), 'cd')
            self.assertEqual(self.dir1.GetTrueName('rot2'), 'rot1')
        def test_GetDir(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddDirSchema(cd)
            cd2 = DirSchema.Create(None, 'cd2')
            self.dir1.AddDirSchema(cd2)
            self.assertEqual(cd2, self.dir1.GetDir('cd2'))
            self.assertEqual(cd, self.dir1.GetDir('cd'))
        def test_GetDirs(self):
            cd = DirSchema.Create(None, 'cd')
            self.dir1.AddDirSchema(cd)
            self.assertTrue('cd' in self.dir1.GetDirs())
        def test_Exclusion_Methods(self):
            dir3 = DirSchema.Create(self.dir1, 'dir3')
            dir4 = DirSchema.Create(self.dir1, 'dir4')
            dir5 = DirSchema.Create(self.dir1, 'dir5')
            self.dir1.SetExclusion('dir2', 'dir3')
            self.dir1.SetMutualExclusion('dir2', 'dir4')
            self.dir1.SetMutualExclusion('dir4', 'dir5')
            self.assertTrue('dir3' in self.dir1.GetExclusions('dir2'))
            self.assertTrue('dir4' in self.dir1.GetExclusions('dir2'))
            self.assertTrue('dir2' in self.dir1.GetExclusions('dir4'))
            self.assertTrue('dir5' in self.dir1.GetExclusions('dir4'))
            self.assertTrue('dir4' in self.dir1.GetExclusions('dir5'))
        def test_GetFather(self):
            self.assertEqual(self.dir2.GetFather(),self.dir1)
        def test_GetFullName(self):
            self.assertEqual(self.dir2.GetFullName().Export(), 'dir1:dir2')
        def test_Inclusion_Methods(self):
            dir3 = DirSchema.Create(self.dir1, 'dir3')
            dir4 = DirSchema.Create(self.dir1, 'dir4')
            dir5 = DirSchema.Create(self.dir1, 'dir5')
            self.dir1.SetInclusion('dir2', 'dir3')
            self.dir1.SetMutualInclusion('dir2', 'dir4')
            self.dir1.SetMutualInclusion('dir4', 'dir5')
            self.assertTrue('dir3' in self.dir1.GetInclusions('dir2'))
            self.assertTrue('dir4' in self.dir1.GetInclusions('dir2'))
            self.assertTrue('dir2' in self.dir1.GetInclusions('dir4'))
            self.assertTrue('dir5' in self.dir1.GetInclusions('dir4'))
            self.assertTrue('dir4' in self.dir1.GetInclusions('dir5'))
        def test_GetName(self):
            self.assertEqual(self.dir1.GetName(), 'dir1')
        def test_ShortCut_Methods(self):
            anything = float('inf')
            self.dir1.SetShortCut(anything)
            self.assertEqual(self.dir1.GetShortCut(), anything)
        def test_Hidden_Methods(self):
            self.dir1.TagHidden('dir2')
            self.assertTrue(self.dir1.IsHidden('dir2'))
        def test_Multiple_Methods(self):
            self.dir1.TagMultiple('dir2')
            self.assertTrue(self.dir1.IsMultiple('dir2'))
        def test_Obsolete_Methods(self):
            self.dir1.TagObsolete('dir2')
            self.assertTrue(self.dir1.IsObsolete('dir2'))
        def test_Optional_Methods(self):
            self.dir1.TagOptional('dir2')
            self.assertTrue(self.dir1.IsOptional('dir2'))
        def test_Add(self):
            pass # @TODO: the add method is not fully implemented. Add"SpecificItem" Methods are implemented.
    unittest.main()
