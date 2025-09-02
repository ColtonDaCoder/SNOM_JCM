'''
Created on Jan 3, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

import os
import sys
import math
import re
import warnings

from jcmwave.__private.decorators import accepts
from jcmwave.__private.system import FilePath
from . import schema_primitives
from . import schema_tree
from . import data_branch 
from .data_tree_exceptions import *

FLOAT_TOKEN = re.compile(r'[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?')

SINGLE_INDENT = ' '

MAX_BUFFER_SIZE = 4096

NUMBER_STOP_TOKENS = set([',', ';', ':', ']', ')', 'i'])
EMPTY_STOP_TOKENS = set()

class TreeReader:
    @accepts(object, FilePath, fileName=FilePath)
    def __init__(self, fileName):
        self.fileName = fileName.Path()
        self.data = ''
        self.pos = 0
        self.buffer = ''
    def Open(self):
        with open(self.fileName, 'r') as f: self.data = f.read()
        self.data += ' '
        self.pos = 0
        # skip header
        if self.TestToken('/*'):
            self.Skip(2)
            while self.pos<len(self.data):
                self.pos += 1
                if self.data[(self.pos-2):(self.pos-1)]=='*/':
                    break
    def FileName(self):
        return self.fileName
    @accepts(object, type, bool, dtype=type, moveForward=bool)
    def Get(self, dtype, moveForward=True, stopTokens=EMPTY_STOP_TOKENS, ignoreSpaces=False):
        success = True
        pos_old = self.TellG()
        movedToToken = True
        if moveForward:
            movedToToken = self.FindToken()
        if dtype == str:
            self.buffer, gotToken = self.__GetToken(stopTokens, ignoreSpaces=ignoreSpaces)
        else:
            self.buffer, gotToken = self.__GetToken(NUMBER_STOP_TOKENS, ignoreSpaces=ignoreSpaces)
        try:
            if (moveForward and not movedToToken or not gotToken):
                raise ParseTreeError('Unable to locate token.', self)
            elif dtype == str:
                rc = self.buffer                
            elif dtype==int:
                try:
                    dat = self.buffer.strip()
                    dat.replace('Inf','inf')
                    rc = int(float(dat))
                except:
                    raise ParseTreeError('Unable to convert to integer.', self)
            elif dtype==float:
                dat = self.buffer.strip()
                dat.replace('Inf','inf')
                try:
                    rc = float(self.buffer)
                except:
                    raise ParseTreeError('Unable to convert to float.', self)
                if self.TestToken('i', False):
                    raise ParseTreeError('Found "i" directly behind float number.', self)
            elif dtype==complex:
                if self.buffer[0]==('('):
                    success_r = True
                    try:
                        rc_r = float(self.buffer[1:])
                    except:
                        success_r = False
                    if not success_r:
                        raise ParseTreeError('Real part (float) of complex number not found.', self)
                    if not self.SkipToken(','):
                        raise ParseTreeError('Part "," of braced complex number not found.', self)
                    rc_i, success_i1 = self.Get(float)
                    success_i2 = self.SkipToken(')')
                    if not success_i1 and success_i2:
                        rc_i = float(0)
                    if not success_i2:
                        raise ParseTreeError('Closing bracket in (*,*)-notation of complex number not found.', self)
                else:
                    try:
                        flt = FLOAT_TOKEN.search(self.buffer)
                        if flt is None:
                            raise Exception
                        rc_r = float(self.buffer[flt.start():flt.end()])
                        remaining_buffer = self.buffer[flt.end():]
                        flt = FLOAT_TOKEN.search(remaining_buffer)
                        if flt!=None:
                            rc_i = float(remaining_buffer[flt.start():flt.end()])
                            if not self.SkipToken('i', False):
                                raise Exception
                        else:
                            rc_i = float(0)
                    except:
                        raise ParseTreeError('Unable to parse complex number in <x>+<y>i format.', self)
                    if self.SkipToken('i', False):
                        rc_i = rc_r
                        rc_r = float(0)
                rc = complex(rc_r, rc_i)
            else:
                raise TypeError('Unsupported type: "%s"' % str(dtype))
        except ParseTreeError:
            self.SeekG(pos_old)
            rc = dtype()
            success = False
        return rc, success
    @accepts(object, (str), bool, token=(str), lookAhead=bool)
    def TestToken(self, token, lookAhead=True):
        old_pos = self.TellG()
        if lookAhead and not self.FindToken():
            self.SeekG(old_pos)
            return False
        if self.data[self.pos:(self.pos+len(token))]!=token:
            self.SeekG(old_pos)
            return False
        else:
            self.SeekG(old_pos)
            return True
    @accepts(object, (str), bool, token=(str), moveForward=bool)
    def SkipToken(self, token, moveForward=True):
        old_pos = self.pos
        try:
            if moveForward and not self.FindToken():
                raise ParseTreeError('No token found.', self)
            if not self.TestToken(token, False):
                raise ParseTreeError('Token not found.', self)
        except ParseTreeError:
            self.pos = old_pos
            return False
        self.Skip(len(token))
        return True
    def TellG(self):
        return self.pos
    def SeekG(self, pos):
        if pos>len(self.data)-1:
            return False
        self.pos = pos
        return True
    def Skip(self, nBytes):
        return self.SeekG(self.pos+nBytes)
    def ReportPosition(self):
        lineNumber = self.data[:self.pos].count('\n')+1
        lastNewLine = self.data[:self.pos].rfind('\n')
        columnNumber = self.pos-lastNewLine
        lineBegin = lastNewLine+1
        nextNewLine = self.data[self.pos:].find('\n')
        if nextNewLine==-1:
            nextNewLine = len(self.data)-self.pos
        lineEnd = self.pos+nextNewLine
        lineContent = self.data[lineBegin:lineEnd]
        return lineContent, lineNumber, columnNumber
    def FindToken(self):
        old_pos = self.pos
        while self.pos < len(self.data):
            if self.data[self.pos]=='#':
                while self.pos<len(self.data) and self.data[self.pos]!='\n':
                    self.pos += 1
            if self.pos==len(self.data):
                break
            currentChar = self.data[self.pos]
            if currentChar>' ':
                return True
            self.pos += 1
        self.pos = old_pos
        return False
    @accepts(object, set, bool, stopTokens=set, ignoreSpaces=bool)
    def __GetToken(self, stopTokens=set(), ignoreSpaces=False):
        whites = set(['\t', '\r', '\n', '\f', '\r', '\v'])
        if self.pos>=len(self.data):
            return False
        pos_offset = 0
        while pos_offset<MAX_BUFFER_SIZE and self.pos+pos_offset<len(self.data):
            currentChar = self.data[self.pos+pos_offset]
            if ((currentChar==' ' and not ignoreSpaces) or
                (currentChar in whites) or
                (currentChar in stopTokens)):
                break
            pos_offset += 1
        out = self.data[self.pos:(self.pos+pos_offset)]
        self.pos += pos_offset
        if len(out)==0:
            success = False
        else:
            success = pos_offset<MAX_BUFFER_SIZE
        return out, success
    def Copy(self):
        raise RuntimeError('TreeReader cannot be copied.')

@accepts(TreeReader, (str), reader=TreeReader, sectionName=(str))
def SkipSection(reader, sectionName=None):
    old_pos = reader.TellG()
    if isinstance(sectionName, str):
        if not reader.TestToken(sectionName):
            return True
    stopTokens = set(['{', '}'])
    dummyToken, success = reader.Get(str, stopTokens=stopTokens)
    if not success:
        return False
    reader.SkipToken('=')
    if not reader.SkipToken('{'):
        reader.SeekG(old_pos)
        return True
    nOpenBrackets = 1
    while nOpenBrackets!=0:
        if reader.SkipToken('{'):
            nOpenBrackets += 1
        elif reader.SkipToken('}'):
            nOpenBrackets -= 1
        else:
            dummyToken, success = reader.Get(str, stopTokens=stopTokens)
            if not success:
                reader.SeekG(old_pos)
                return False
    return True

def WriteTreeDir(treeDir, indentation=0):
    returnString = ''
    primitiveDataMap = treeDir.GetPrimitives()
    for primIter in primitiveDataMap.items():
        returnString += '\n'+SINGLE_INDENT*indentation+str(primIter[0][0])
        if primIter[0][1]>0:
            returnString += '('+str(primIter[0][1])+')'
        returnString += ' = '+primIter[1].Write()
    branchDataMap = treeDir.GetDirs()
    for branchIter in branchDataMap.items():
        branchName = ''
        branchName = branchIter[0][0]
        returnString += '\n'+SINGLE_INDENT*indentation+branchName+' {'
        returnString += WriteTreeDir(branchIter[1], indentation+2)
        returnString += '\n'+SINGLE_INDENT*indentation+'}'
    return returnString

#@accepts(schema_tree.DirSchema, data_branch.TreeDir, TreeReader, set, set,
#         prototypeTreeDir=schema_tree.DirSchema,
#         father=data_branch.TreeDir,
#         reader=TreeReader,
#         rejectedItems=set,
#         ignoredItems=set)
def ParseTreeDir(prototypeTreeDir,
                 father,
                 reader,
                 rejectedItems=set(),
                 ignoredItems=set()):
    stopTokens = set(['{', '}', '='])
    readData = set()
    exclusions = {}
    inclusions = {}
    hasSon = len(prototypeTreeDir.GetChoiceDirs())>0
    prototypeTreeDirName = prototypeTreeDir.GetName()
    tokenNameDefault = {}
    if len(prototypeTreeDirName)>3:
        stringLength = len(prototypeTreeDirName)
        bagPart = prototypeTreeDirName[stringLength-3:]
        if bagPart=='Bag':
            tokenNameDefault[0] = prototypeTreeDirName[:-3]
    # downward compatibility: skip nonexist. directories XYBag
    skipLevel=0
    # read tree from file
    while reader!=None and reader.FindToken():
        if reader.SkipToken('}'):
            if skipLevel==0:
                break
            skipLevel -= 1
            continue
        tokenName = ''
        pos_beforeToken = reader.TellG()
        tokenName, success = reader.Get(str, stopTokens=stopTokens)
        if len(tokenName)==0:
            if len(tokenNameDefault[skipLevel])!=0:
                tokenName = tokenNameDefault[skipLevel]
            else:
                raise ParseTreeError('Parser error:', reader)
        tokenNameTrue = prototypeTreeDir.GetTrueName(tokenName)
        isMultiple = prototypeTreeDir.IsMultiple(tokenNameTrue)
        if tokenNameTrue in rejectedItems:
            raise UnknownKeyword(reader, tokenName)
        if tokenNameTrue in exclusions:
            raise ExclusionError(reader, tokenName, exclusions[tokenNameTrue])
        excludedItems = list(prototypeTreeDir.GetExclusions(tokenNameTrue))
        for excludedItem in excludedItems:
            if excludedItem in readData:
                raise ExclusionError(reader, excludedItem, tokenName)
            exclusions[excludedItem] = tokenNameTrue
        includedItems = list(prototypeTreeDir.GetInclusions(tokenNameTrue))
        for includedItem in includedItems:
            inclusions[includedItem] = tokenNameTrue
        prototypePrimitive = prototypeTreeDir.GetPrimitive(tokenNameTrue)
        prototypeTreeItem = prototypeTreeDir.GetDir(tokenNameTrue)
        adaptor = prototypeTreeDir.GetAdaptor(tokenNameTrue)
        if prototypePrimitive is None and prototypeTreeItem!=None:
            prototypePrimitive = prototypeTreeItem.GetShortCut()
        equalSignRead = reader.SkipToken('=')
        if prototypePrimitive!=None and prototypeTreeItem!=None:
            if reader.TestToken('{',True):
                prototypePrimitive = None
            else:
                prototypeTreeItem = None
        if prototypePrimitive!=None and not equalSignRead:
            raise MissingEqualSign(reader)
        if (prototypeTreeDirName=='Constant' and
            len(tokenName)>4 and
            tokenName[:5]=='Entry' and
            prototypeTreeDir.GetPrimitive('Tensor')!=None):
            #
            reader.SeekG(pos_beforeToken)
            prototypePrimitive = prototypeTreeDir.GetPrimitive('Tensor')
            tokenName = 'Tensor'
            tokenNameTrue = tokenName
        if prototypePrimitive!=None:
            if not isMultiple and tokenNameTrue in readData:
                raise DataRedefinition(reader, tokenName)
            primitive = prototypePrimitive.CreateTreePrimitive()
            if not primitive.Read(reader):
                raise InvalidPrimitive(reader, prototypePrimitive.TypeName())
            if not prototypePrimitive.CheckRange(primitive):
                raise PrimitiveOutOfRange(reader)
            if prototypeTreeDir.IsObsolete(tokenNameTrue):
                dummyException = ParseTreeError('', reader)
                warnings.warn('%s Tag "%s" is obsolete.' % (str(dummyException), tokenName))
            else:
                father.AddPrimitive(tokenNameTrue, primitive)
            readData.add(tokenNameTrue)
            continue
        if prototypeTreeItem!=None:
            if not isMultiple and tokenNameTrue in readData:
                raise DataRedefinition(reader, tokenName)
            if tokenNameTrue in ignoredItems:
                SkipSection(reader)
                continue
            subDir = father.Create(tokenNameTrue)
            if tokenName!=tokenNameTrue:
                subDir.SetAlias(tokenName)
            if not reader.SkipToken('{'):
                raise MissingDirOpenBracket(reader)
            ParseTreeDir(prototypeTreeItem, subDir, reader)
            father.AddTreeDir(subDir)
            readData.add(tokenNameTrue)
            continue
        if adaptor!=None:
            dummyException = ParseTreeError('', reader)
            warnings.warn('%s Tag "%s" is obsolete.' % (str(dummyException), tokenName))
            if not isMultiple and tokenNameTrue in readData:
                raise DataRedefinition(reader, tokenName)
            if tokenNameTrue in ignoredItems:
                SkipSection(reader)
                continue
            if not reader.SkipToken('{'):
                raise MissingDirOpenBracket(reader)
            originalTree = father.Create(tokenNameTrue)
            ParseTreeDir(adaptor.schema, originalTree, reader)
            path = originalTree.FinalDir().GetFullName()
            while path.Size()>0:
                if path in adaptor.treeAdaptors:
                    break
                path.PopBack()
            if path.Size()==0:
                continue
            transformedTree = adaptor.treeAdaptors[path].Transform(originalTree.Get())
            primitives = transformedTree.GetPrimitives()
            for primIter in primitives.items():
                itemName = primIter[0]
                if not prototypeTreeDir.IsMultiple(itemName) and itemName in readData:
                    raise DataRedefinition(reader, itemName)
                father.Add(itemName, primIter[1].Copy())
                readData.add(itemName)
            dirs = transformedTree.GetDirs()
            for dirIter in dirs:
                itemName = dirIter[0][0]
                if not prototypeTreeDir.IsMultiple(itemName) and itemName in readData:
                    raise DataRedefinition(reader, itemName)
                father.Add(dirIter[1].Copy())
                readData.add(itemName)
            if father.GetTrunkdir()!=None and transformedTree.GetTrunkDir()!=None:
                raise ExclusionError(reader, father.GetTrunkDir().GetName(), transformedTree.GetTrunkDir().GetName())
            if transformedTree.GetTrunkDir()!=None:
                father.SetTrunkDir(transformedTree.GetTrunkDir().GetName())
            readData.add(tokenNameTrue)
            continue
        if tokenName.find('.')!=-1:
            raise UnknownKeyword(reader, tokenName)
        son = prototypeTreeDir.GetChoiceDir(tokenNameTrue)
        if son is None:
            if prototypeTreeDir.IsDummyDir(tokenNameTrue):
                skipLevel += 1
                if not reader.SkipToken('{'):
                    raise MissingDirOpenBracket(reader)
                father.AddDummyDir(tokenNameTrue)
                dummyException = ParseTreeError('', reader)
                warnings.warn('%s Tag "%s" is obsolete.' % (str(dummyException), tokenName))
                continue
            # downward compatibility: non-existing XYBags are ignored
            stringLength = len(tokenNameTrue)
            if stringLength>3 and tokenNameTrue[-3:]=='Bag':
                skipLevel += 1
                tokenNameDefault[skipLevel] = tokenNameTrue[:-3]
                if not reader.SkipToken('{'):
                    raise MissingDirOpenBracket(reader)
                continue
            else:
                # downward compatibility: parse vector V = [VX VY VZ]
                if ParseLegacy3Vector(tokenNameTrue, prototypeTreeDir, father, reader):
                    actualTokenName = tokenNameTrue[:-1]
                    readData.add(actualTokenName)
                    continue
                else:
                    raise UnknownKeyword(reader, tokenName)
        if not isMultiple and tokenNameTrue in readData:
            raise DataRedefinition(reader, tokenName)
        if father.GetTrunkDir()!=None:
            raise ExclusionError(reader, father. GetTrunkDir().GetName(), tokenName)
        if not reader.SkipToken('{'):
            raise MissingDirOpenBracket(reader)
        son_ = father.Create(son.GetName(), father)
        ParseTreeDir(son, son_, reader)
        father.SetTrunkDir(son.GetName())
        # end while reader!=None and reader.FindToken()
    # fill default values into tree
    prototypeTrees = prototypeTreeDir.GetDirs()
    for treeIter in prototypeTrees.items():
        if prototypeTreeDir.IsOptional(treeIter[0]):
            continue
        if prototypeTreeDir.IsObsolete(treeIter[0]):
            continue
        if (treeIter[0] not in readData and
            treeIter[0] not in rejectedItems and
            treeIter[0] not in ignoredItems and
            treeIter[0] not in exclusions and
            not prototypeTreeDir.IsMultiple(treeIter[0])):
            try:
                subDir = father.Create(treeIter[0])
                ParseTreeDir(treeIter[1], subDir, None)
                father.Add(subDir)
                readData.add(treeIter[0])
            except MissingDefault:
                raise MissingDefault(reader, treeIter[0])
            except MissingDefaultSonDir:
                raise MissingDefault(reader, treeIter[0])
    prototypePrimitives = prototypeTreeDir.GetPrimitives()
    for primitiveIter in prototypePrimitives.items():
        if (primitiveIter[0][1]>0): continue
        if prototypeTreeDir.IsOptional(primitiveIter[0][0]):
            continue
        if prototypeTreeDir.IsObsolete(primitiveIter[0][0]):
            continue
        if (primitiveIter[0][0] not in readData and
            primitiveIter[0][0] not in rejectedItems and
            primitiveIter[0][0] not in ignoredItems and
            primitiveIter[0][0] not in exclusions and
            not prototypeTreeDir.IsMultiple(primitiveIter[0][0])):
            #
            if not primitiveIter[1].HasDefault():
                raise MissingDefault(reader, primitiveIter[0][0])
            primitive = primitiveIter[1].CreateTreePrimitive()
            father.Add(primitiveIter[0][0], primitive)
            readData.add(primitiveIter[0][0])
        for iter in inclusions.items():
            if iter[0] not in readData:
                raise InclusionError(reader, iter[0], iter[1])
        if hasSon and father.GetTrunkDir()==None:
            son = prototypeTreeDir.DefaultChoiceDir()
            if son==None:
                raise MissingDefaultSonDir(reader)
            son_ = father.Create(son.GetName(), father)
            ParseTreeDir(son, son_, None)
            father.SetTrunkDir(son.GetName())


# additional methods
def ParseLegacy3VectorComponent(dtype, tokenName, schema, treeDir, reader, comp):
    if schema is None:
        return False
    value, success = reader.Get(dtype)
    if not success:
        return False
    if treeDir.GetPrimitive(tokenName) is None:
        treeDir.AddPrimitive(tokenName, schema.CreateTreePrimitive())
    actualVector = None
    if isinstance(schema, schema_primitives.TensorSchema) and schema.rank==1:
        actualVector = treeDir.GetPrimitive(tokenName).GetValue().entries
    elif isinstance(schema, schema_primitives.VectorSchema):
        actualVector = treeDir.GetPrimitive(tokenName).GetValue()
        if len(actualVector)==0: # just created, w/o default
            for ii in range(3):
                actualVector.append(dtype(0))
    if actualVector is None or len(actualVector)!=3:
        return False
    actualVector[comp] = value
    return True

def ParseLegacy3Vector(tokenName, prototypeTreeDir, treeDir, reader):
    stringLength = len(tokenName)
    if stringLength<2:
        return False
    comp = -1
    if tokenName[stringLength-1]=='X':
        comp = 0
    elif  tokenName[stringLength-1]=='Y':
        comp = 1
    elif  tokenName[stringLength-1]=='Z':
        comp = 2
    if comp==-1:
        return False
    actualTokenName = tokenName[:-1]
    prototypePrimitive = prototypeTreeDir.GetPrimitive(actualTokenName)
    if prototypePrimitive is None:
        return False
    if isinstance(prototypePrimitive, schema_primitives.TensorSchema) and prototypePrimitive._rank==1:
        if ParseLegacy3VectorComponent(complex, actualTokenName, prototypePrimitive, treeDir, reader, comp):
            return True
    if isinstance(prototypePrimitive, schema_primitives.VectorSchema):
        if ParseLegacy3VectorComponent(prototypePrimitive._type, actualTokenName, prototypePrimitive, treeDir, reader, comp):
            return True
    return False



def ReadString(dtype, reader, quotMarks=False):
    if quotMarks:
        if not reader.SkipToken('"'):
            raise MissingStringOpenQuotMark(reader)
        stopTokens = set(['"'])
        ignoreSpaces = True
    else:
        stopTokens = set()
        ignoreSpaces = False
    readValue, success = reader.Get(dtype, stopTokens=stopTokens, ignoreSpaces=ignoreSpaces)
    if not success:
        return '', False
    if quotMarks and not reader.SkipToken('"'):
        raise MissingStringCloseQuotMark(reader)
    string_pos = 0
    while string_pos<len(readValue)-1:
        string_pos = readValue.find('$', string_pos)
        key = ''
        replacedSubValue = ''
        found = False
        string_pos_start = string_pos
        string_pos += 1
        while string_pos<len(readValue) and readValue[string_pos]!='$':
            key_ = key+readValue[string_pos]
            _replacedSubValue = os.getenv(key_, '')
            if len(_replacedSubValue)==0:
                if found:
                    break
            key = key_
            if len(_replacedSubValue)!=0:
                replacedSubValue = _replacedSubValue
                found = True
            if key=='THIS':
                found = True
                break
            string_pos += 1
        if found:
            if key=='THIS':
                filePath = FilePath(reader.FileName())
                replacedSubValue = filePath.BaseName()
            keyLength = len(key)
            subStringBeforeReplacementLocation = readValue[:string_pos_start]
            subStringAfterReplacementLocation = readValue[string_pos+1:]
            readValue = (subStringBeforeReplacementLocation+
                         replacedSubValue+
                         subStringAfterReplacementLocation)
            string_pos = string_pos_start+len(replacedSubValue)
    return readValue, True

def ParseNumberVectorAsList(dtype, reader):
    entryList = []
    if not reader.SkipToken('['):
        readEntry, success = reader.Get(dtype)
        if not success:
            return [], False
        entryList.append(readEntry)
        return entryList, True
    while True:
        while reader.TestToken('['):
            readList, success = ParseNumberVectorAsList(dtype, reader)
            if not success:
                return [], False
            entryList.extend(readList)
            reader.SkipToken(',')
        if reader.SkipToken(']'):
            return entryList, True
        readEntry, success = reader.Get(dtype)
        if not success:
            return [], False
        entryList.append(readEntry)
        if reader.SkipToken(':'):
            if isinstance(readEntry, complex):
                if readEntry.imag!=0.0:
                    return [], False
                else:
                    lowerBound = readEntry.real
            else:
                try:
                    lowerBound = float(readEntry)
                except:
                    return [], False
            readEntry, success = reader.Get(dtype)
            if not success:
                return False
            if isinstance(readEntry, complex):
                if readEntry.imag!=0.0:
                    return [], False
                else:
                    step = readEntry.real
            else:
                try:
                    step = float(readEntry)
                except:
                    return [], False
            if not reader.SkipToken(':'):
                return False
            readEntry, success = reader.Get(dtype)
            if not success:
                return False
            if isinstance(readEntry, complex):
                if readEntry.imag!=0.0:
                    return [], False
                else:
                    upperBound = readEntry.real
            else:
                try:
                    upperBound = float(readEntry)
                except:
                    return [], False
            scaling = max([math.fabs(upperBound-lowerBound), math.fabs(step)])
            newEntry = lowerBound+step
            iStep = 1
            if step.real>0.0:
                while(float(upperBound-newEntry)/scaling>-1e-12):
                    entryList.append(dtype(newEntry))
                    iStep += 1
                    newEntry = lowerBound+float(iStep)*step
            elif step.real<0.0:
                while(float(upperBound-newEntry)/scaling>1e-12):
                    entryList.append(dtype(newEntry))
                    iStep += 1
                    newEntry = lowerBound+float(iStep)*step
            if math.fabs(upperBound-newEntry+step)/scaling<1e-12:
                entryList.pop(-1)
                entryList.append(upperBound)
            if reader.SkipToken(']'):
                return entryList, True
            else:
                return [], False
        if reader.SkipToken(','):
            if reader.SkipToken(']'):
                return [], False
    return entryList, True

def FormatXYZ(ii):
    if ii==1:
        return 'X'
    elif ii==2:
        return 'Y'
    elif ii==3:
        return 'Z'
    else:
        sys.exit(1)

def ParseLegacyTensorFormat(dtype, rank, reader):
    pos_old = reader.TellG()
    entryList = []
    index = [int(0)]*(rank+1)
    index[0] = float('nan')
    inBrackets = reader.SkipToken('{')
    tensorTree = schema_tree.DirSchema.Create(name='TensorDir')
    for ii in range(1,rank+1):
        index[ii] = int(1)
    while index[1]<=3:
        oStream = 'Entry'
        for r in range(1,rank+1):
            oStream += FormatXYZ(index[r])
        zero = dtype(0)
        entry = schema_primitives.NumberSchema.Create(zero, dtype=dtype)
        tensorTree.AddPrimitive(oStream, entry)
        r = rank
        while r>0:
            if index[r]<3 or r==1:
                index[r] += 1
                break
            else:
                index[r] = int(1)
                r = r-1
    tensorDir = data_branch.TreeDir.Create('Tensor')
    try:
        ParseTreeDir(tensorTree, tensorDir, reader)
    except ParseTreeError as err:
        reader.SeekG(pos_old)
        print('\nParse Error: '+err.message+'\n')
        return [], False
    for ii in range(1,rank+1):
        index[ii] = int(1)
    while index[rank]<=3:
        oStream = 'Entry'
        for r in range(rank, 0,-1):
            oStream += FormatXYZ(index[r])
        try:
            value = dtype(tensorDir.GetPrimitive(oStream).GetValue())
        except:
            return [], False
        entryList.append(value)
        r = 1
        while r<=rank:
            if index[r]<3 or r==rank:
                index[r] += 1
                break
            else:
                index[r] = 1
                r += 1
    if not inBrackets:
        reader.SeekG(pos_old)
        reader.SkipToken('{')
        stopTokens = set('}')
        while True:
            dummy, success = reader.Get(str, stopTokens=stopTokens)
            if not success:
                break
            if reader.TestToken('}'):
                break
    return entryList, True

def ParseLegacyRotationFormat(reader):
    entryMatrix = [[],[],[]]
    for ii in range(3):
        for jj in range(3):
            entryMatrix[ii].append(float(0))
    zero = float(0)
    rotationTree = schema_tree.DirSchema.Create(name='RotationTree')
    eulerAngle = schema_tree.DirSchema.Create(rotationTree, 'EulerAngle')
    eulerAngle.AddPrimitive('Phi', schema_primitives.NumberSchema.Create(zero, dtype=float))
    eulerAngle.AddPrimitive('Theta', schema_primitives.NumberSchema.Create(zero, dtype=float))
    eulerAngle.AddPrimitive('Psi', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix = schema_tree.DirSchema.Create(rotationTree, 'RotationMatrix')
    one = float(1.0)
    rotationMatrix.AddPrimitive('EntryXX', schema_primitives.NumberSchema.Create(one, dtype=float))
    rotationMatrix.AddPrimitive('EntryXY', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix.AddPrimitive('EntryXZ', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix.AddPrimitive('EntryYX', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix.AddPrimitive('EntryYY', schema_primitives.NumberSchema.Create(one, dtype=float))
    rotationMatrix.AddPrimitive('EntryYZ', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix.AddPrimitive('EntryZX', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix.AddPrimitive('EntryZY', schema_primitives.NumberSchema.Create(zero, dtype=float))
    rotationMatrix.AddPrimitive('EntryZZ', schema_primitives.NumberSchema.Create(one, dtype=float))
    rotDirRoot = data_branch.TreeDir.Create('Rotation')
    try:
        ParseTreeDir(rotationTree, rotDirRoot, reader)
    except ParseTreeError:
        return [], False
    rotDir = rotDirRoot.GetTrunkDir()
    phi = float(0)
    theta = float(0)
    psi = float(0)
    if rotDir.GetName()=='EulerAngle':
        phi = float(rotDir.GetPrimitive('Phi').GetValue())/180.*math.pi
        theta = float(rotDir.GetPrimitive('Theta').GetValue())/180.*math.pi
        psi = float(rotDir.GetPrimitive('Psi').GetValue())/180.*math.pi
        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        cos_psi = math.cos(psi)
        sin_psi = math.sin(psi)
        entryMatrix[0][0] = cos_psi*cos_theta*cos_phi-sin_psi*sin_phi;
        entryMatrix[1][0] = cos_psi*cos_theta*sin_phi+sin_psi*cos_phi;
        entryMatrix[2][0] = -cos_psi*sin_theta;
        entryMatrix[0][1] = -sin_psi*cos_theta*cos_phi-cos_psi*sin_phi;
        entryMatrix[1][1] = -sin_psi*cos_theta*sin_phi+cos_psi*cos_phi;
        entryMatrix[2][1] = sin_psi*sin_theta;
        entryMatrix[0][2] = sin_theta*cos_phi;
        entryMatrix[1][2] = sin_theta*sin_phi;
        entryMatrix[2][2] = cos_theta;
    elif rotDir.GetName()=='RotationMatrix':
        entryMatrix[0][0] = float(rotDir.GetPrimitive('EntryXX').GetValue())
        entryMatrix[1][0] = float(rotDir.GetPrimitive('EntryYX').GetValue())
        entryMatrix[2][0] = float(rotDir.GetPrimitive('EntryZX').GetValue())
        entryMatrix[0][1] = float(rotDir.GetPrimitive('EntryXY').GetValue())
        entryMatrix[1][1] = float(rotDir.GetPrimitive('EntryYY').GetValue())
        entryMatrix[2][1] = float(rotDir.GetPrimitive('EntryZY').GetValue())
        entryMatrix[0][2] = float(rotDir.GetPrimitive('EntryXZ').GetValue())
        entryMatrix[1][2] = float(rotDir.GetPrimitive('EntryYZ').GetValue())
        entryMatrix[2][2] = float(rotDir.GetPrimitive('EntryZZ').GetValue())
    for ii in range(3):
        for jj in range(3):
            if math.fabs(entryMatrix[ii][jj])<1e-14:
                entryMatrix[ii][jj] = float(0)
    return entryMatrix, True


if __name__=='__main__':
    # redefine open to be file independent
    def OpenString(self, string):
        self.data = string+' '
        self.buffer = ''
        self.pos = 0
    TreeReader.Open = OpenString
    # unittesting
    import unittest
    class Test_TreeReader(unittest.TestCase):
        def setUp(self):
            self.fileName = '/a/b/c/d'
            self.filePath = FilePath(self.fileName)
            self.reader = TreeReader(self.filePath)
        def test_ReportPosition(self):
            test_data = '\n\n First Test\n'
            self.reader.Open(test_data)
            self.reader.FindToken()
            self.assertEqual(self.reader.ReportPosition(), (' First Test', 3, 2))
        def test_FileName(self):
            self.assertEqual(self.reader.FileName(), self.fileName)
        def test_SeekG_TellG_Skip(self):
            test_data = '\n\n First Test\n'
            self.reader.Open(test_data)
            self.assertTrue(self.reader.SeekG(8))
            self.assertFalse(self.reader.SeekG(100))
            self.assertEqual(self.reader.TellG(),8)
            self.assertTrue(self.reader.Skip(2))
            self.assertEqual(self.reader.TellG(),10)
            self.assertFalse(self.reader.Skip(20))
        def test_Get(self):
            # Get(self, dtype, moveForward=True, stopTokens=EMPTY_STOP_TOKENS, ignoreSpaces=False)
            #
            # test dtype=unicode
            test_data = 'abc'
            self.reader.Open(test_data)
            val, success = self.reader.Get(str)
            self.assertTrue(success)
            self.assertEqual(val, 'abc')            
            # test dtype=str, moveForward=True
            test_data = '   abc   '
            self.reader.Open(test_data)
            val, success = self.reader.Get(str)
            self.assertTrue(success)
            self.assertEqual(val, 'abc')
            # test dtype=str, moveForward=False
            self.reader.SeekG(0)
            val, success = self.reader.Get(str, moveForward=False)
            self.assertFalse(success)
            # test dtype=str, moveForward=True, stopTokens=set([some tokens])
            test_data = '   ab=c   '
            self.reader.Open(test_data)
            val, success = self.reader.Get(str, stopTokens=set(['=']))
            self.assertTrue(success)
            self.assertEqual(val, 'ab')
            # test dtype=str, moveForward=True, stopTokens=set([some tokens]), ignoreSpaces=True
            test_data = '   ab de =c   '
            self.reader.Open(test_data)
            val, success = self.reader.Get(str, stopTokens=set(['=']), ignoreSpaces=True)
            self.assertTrue(success)
            self.assertEqual(val, 'ab de ')
            # test dtype=int, moveForward=True, stopTokens=NUMBER_STOP_TOKENS
            test_data = '   17  '
            self.reader.Open(test_data)
            val, success = self.reader.Get(int)
            self.assertTrue(success)
            self.assertEqual(val, int(17))
            test_data = '   17.0  '
            self.reader.Open(test_data)
            val, success = self.reader.Get(int)
            self.assertTrue(success)
            self.assertEqual(val, int(17))
            # test dtype=float, moveForward=True, stopTokens=NUMBER_STOP_TOKENS
            test_data = '   17  '
            self.reader.Open(test_data)
            val, success = self.reader.Get(float)
            self.assertTrue(success)
            self.assertEqual(val, float(17))
            test_data = '   +17.5e-12  '
            self.reader.Open(test_data)
            val, success = self.reader.Get(float)
            self.assertTrue(success)
            self.assertEqual(val, float(17.5e-12))
            # test dtype=complex, moveForward=True, stopTokens=NUMBER_STOP_TOKENS
            test_data = '   (17,1)  '
            self.reader.Open(test_data)
            val, success = self.reader.Get(complex)
            self.assertTrue(success)
            self.assertEqual(val, complex(17,1))
            test_data = '   +17.5e-12+3.5i  '
            self.reader.Open(test_data)
            val, success = self.reader.Get(complex)
            self.assertTrue(success)
            self.assertEqual(val, complex(17.5e-12, 3.5))
        def test_TestToken(self):
            test_data = '\n\n MyDir =  { First Test }\n'
            self.reader.Open(test_data)
            self.reader.FindToken()
            self.assertTrue(self.reader.TestToken('MyDir', lookAhead=False))
            self.assertFalse(self.reader.TestToken('NotMyDir', lookAhead=False))
            self.reader.SeekG(0)
            self.assertTrue(self.reader.TestToken('MyDir', lookAhead=True))
            self.assertFalse(self.reader.TestToken('NotMyDir', lookAhead=True))
        def test_FindToken_SkipToken(self):
            test_data = '\n\n MyDir =  { First Test }\n'
            self.reader.Open(test_data)
            self.reader.FindToken()
            pos_old = self.reader.TellG()
            self.assertEqual(pos_old, 3)
            self.assertTrue(self.reader.SkipToken('MyDir', moveForward=False))
            self.assertTrue(self.reader.TestToken('=', lookAhead=True))
            self.reader.SeekG(pos_old)
            self.assertFalse(self.reader.SkipToken('NotMyDir', moveForward=False))
            self.reader.SeekG(0)
            self.assertTrue(self.reader.SkipToken('MyDir', moveForward=True))
        def test_Copy(self):
            self.assertRaises(RuntimeError, self.reader.Copy)
    class Test_SkipSection(unittest.TestCase):
        def setUp(self):
            self.fileName = '/a/b/c/d'
            self.filePath = FilePath(self.fileName)
            self.reader = TreeReader(self.filePath)
        def test_SkipSection(self):
            mySection = '''\
    nonsense = {
        more nonsense {
            and more {
                we may also have something in here
            }
        }
    }
'''
            self.reader.Open(mySection)
            self.assertTrue(SkipSection(self.reader))
            self.assertEqual(self.reader.TellG(), len(mySection)-1)
            self.reader.SeekG(0)
            self.assertTrue(SkipSection(self.reader, 'NoNonsense'))
            self.assertEqual(self.reader.TellG(),0)
            self.assertTrue(SkipSection(self.reader, 'nonsense'))
            self.assertEqual(self.reader.TellG(), len(mySection)-1)
            self.reader.Open(mySection[:-2])
            self.assertFalse(SkipSection(self.reader))
    class Test_WriteTreeDir(unittest.TestCase):
        def test_WriteTreeDir(self):
            root = data_branch.TreeDir.Create('Root')
            l11 = data_branch.TreeDir.Create('L11')
            l12 = data_branch.TreeDir.Create('L12')
            l21 = data_branch.TreeDir.Create('L21')
            l22 = data_branch.TreeDir.Create('L22')
            root.AddTreeDir(l11)
            root.AddTreeDir(l12)
            l12.AddTreeDir(l21)
            l12.AddTreeDir(l22)
            from . import data_primitives
            p1 = data_primitives.NumberPrimitive(1,complex)
            p2 = data_primitives.NumberPrimitive(1,float)
            p3 = data_primitives.StringPrimitive(True, 'the string')
            p4 = data_primitives.StringPrimitive(False, 'myString')
            p5 = data_primitives.VectorPrimitive((1,2,3,4), complex)
            l11.AddPrimitive('p1', p1)
            l11.AddPrimitive('p2', p2)
            l12.AddPrimitive('p3', p3)
            l21.AddPrimitive('p4', p4)
            l22.AddPrimitive('p5', p5)
            val = WriteTreeDir(root)
            expectedValue = '''
L12 {
  p3 = "the string"
  L22 {
    p5 = [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0)]
  }
  L21 {
    p4 = myString
  }
}
L11 {
  p1 = (1.0, 0.0)
  p2 = 1.0
}'''
            self.assertEqual(val, expectedValue)
    class Test_ParseTreeDir_ReadString_ParseNumberVectorAsList(unittest.TestCase):
        def test_Case(self):
            expectedValue = '''
L12 {
  p3 = "the string"
  L22 {
    p5 = [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0)]
  }
  L21 {
    p4 = myString
  }
}
L11 {
  p1 = (1.0, 0.0)
  p2 = 1.0
}'''
            reader = TreeReader(FilePath('/a/b/c'))
            reader.Open(expectedValue)
            root = schema_tree.DirSchema.Create(None, 'Root')
            l11 = schema_tree.DirSchema.Create(None, 'L11')
            l12 = schema_tree.DirSchema.Create(None, 'L12')
            l21 = schema_tree.DirSchema.Create(None, 'L21')
            l22 = schema_tree.DirSchema.Create(None, 'L22')
            root.AddDirSchema(l11)
            root.AddDirSchema(l12)
            l12.AddDirSchema(l21)
            l12.AddDirSchema(l22)
            p1 = schema_primitives.NumberSchema.Create(dtype=complex)
            p2 = schema_primitives.NumberSchema.Create(dtype=float)
            p3 = schema_primitives.StringSchema.Create()
            p4 = schema_primitives.StringSchema.Create()
            p5 = schema_primitives.VectorSchema.Create(dtype=complex)
            l11.AddPrimitive('p1', p1)
            l11.AddPrimitive('p2', p2)
            l12.AddPrimitive('p3', p3)
            l21.AddPrimitive('p4', p4)
            l22.AddPrimitive('p5', p5)
            tdFather = data_branch.TreeDir('Root')
            ParseTreeDir(root, tdFather, reader)
            self.assertEqual(WriteTreeDir(tdFather), expectedValue)
    class Test_ParseLegacy3VectorComponent(unittest.TestCase):
        # ParseLegacy3VectorComponent(dtype, tokenName, schema, treeDir, reader, comp)
        def test_Case(self):
            expectedValue = ' 5+3i'
            reader = TreeReader(FilePath('/a/b/c'))
            reader.Open(expectedValue)
            dtype = complex
            tokenName = 'Test'
            schema = schema_primitives.VectorSchema.Create(dtype)
            treeDir = data_branch.TreeDir.Create('dir1')
            comp = 2
            ParseLegacy3VectorComponent(dtype, tokenName, schema, treeDir, reader, comp)
            self.assertEqual(tuple(treeDir.GetPrimitive('Test').GetValue()), (0j, 0j, 5+3j))
    class Test_ParseLegacy3Vector(unittest.TestCase):
        # ParseLegacy3Vector(tokenName, prototypeTreeDir, treeDir, reader)
        def test_Case(self):
            expectedValue = '''
            StrengthX = (1.0, 0)
            StrengthY = (2.0,0)
            StrengthZ = (3.0,1)
            '''
            reader = TreeReader(FilePath('/a/b/c'))
            reader.Open(expectedValue)
            dtype = complex
            tokenName = 'Strength'
            ptDir = schema_tree.DirSchema.Create(None, 'Test')
            vecSchema = schema_primitives.VectorSchema.Create(dtype=dtype)
            ptDir.AddPrimitive('Strength', vecSchema)
            treeDir = data_branch.TreeDir.Create('Test')
            # ParseTreeDir(prototypeTreeDir, father, reader, rejectedItems, ignoredItems)
            ParseTreeDir(ptDir, treeDir, reader)
            self.assertEqual(tuple(treeDir.GetPrimitive('Strength').GetValue()), (1+0j, 2+0j, 3+1j))
    class Test_ParseLegacyTensorFormat(unittest.TestCase):
        # ParseLegacyTensorFormat(dtype, rank, reader)
        def test_Case(self):
            expectedValue = '''
            {
            EntryXX = (1.0, 9)
            EntryXY = (2.0, 8)
            EntryXZ = (3.0, 7)
            EntryYX = (4.0, 6)
            EntryYY = (5.0, 5)
            EntryYZ = (6.0, 4)
            EntryZX = (7.0, 3)
            EntryZY = (8.0, 2)
            EntryZZ = (9.0, 1)
            }
            '''
            reader = TreeReader(FilePath('/a/b/c'))
            reader.Open(expectedValue)
            dtype = complex
            rank = 2
            entryList, success = ParseLegacyTensorFormat(dtype, rank, reader)
            self.assertTrue(success)
            self.assertEqual(tuple(entryList), ((1+9j), (2+8j), (3+7j), (4+6j), (5+5j), (6+4j), (7+3j), (8+2j), (9+1j)))
    class Test_ParseLegacyRotationFormat(unittest.TestCase):
        # ParseLegacyRotationFormat(reader)
        def test_Case(self):
            expectedValue = '''
            RotationMatrix = {
            EntryXX = 1.0
            EntryXY = 2.0
            EntryXZ = 3.0
            EntryYX = 4.0
            EntryYY = 5.0
            EntryYZ = 6.0
            EntryZX = 7.0
            EntryZY = 8.0
            EntryZZ = 9.0
            }
            '''
            reader = TreeReader(FilePath('/a/b/c'))
            reader.Open(expectedValue)
            entryMatrix, success = ParseLegacyRotationFormat(reader)
            self.assertTrue(success)
            self.assertEqual(tuple([tuple(x) for x in entryMatrix]), ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0), (7.0, 8.0, 9.0)))
            expectedValue = '''
            EulerAngle = {
            Phi = 90
            Theta = 0
            Psi = 0
            }
            '''
            reader = TreeReader(FilePath('/a/b/c'))
            reader.Open(expectedValue)
            entryMatrix, success = ParseLegacyRotationFormat(reader)
            self.assertTrue(success)
            self.assertEqual(tuple([tuple(x) for x in entryMatrix]), ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    class Test_ParseError(unittest.TestCase):
        def test_PE(self):
            fileName = FilePath('/a/b/c/d')
            reader = TreeReader(fileName)
            test_data = '\n\n First Test\n'
            reader.Open(test_data)
            reader.FindToken()
            a = ParseTreeError('Additional Info.', reader)
            result = str(a)
            expectation = 'File "/a/b/c/d", line: 3, column: 2\n>>>  First Test\nAdditional Info.'
            self.assertEqual(result, expectation)
    unittest.main()

