'''
Created on Feb 4, 2011

@author: Daniel Lockau <lockau@zib.de>
'''

class ParseTreeError(RuntimeError):
    def __init__(self, s, reader):
        if reader is None:
            self.filename = "NULL"
            self.lineContent = "NULL"
            self.lineNumber = 0
            self.columnNumber = 0
        else:
            self.filename = reader.FileName()
            self.lineContent, self.lineNumber, self.columnNumber = \
                              reader.ReportPosition()
        self.errmessage = s
        self.message = 'File "%s", line: %d, column: %d\n>>> %s\n' % \
            (self.filename, self.lineNumber, self.columnNumber, self.lineContent)
        self.message += s
    def __str__(self):
        return self.message

class InvalidObjectName(ParseTreeError):
    def __init__(self, reader, readObjectName, expectedObjectName):
        additional_info = 'expected: "%s", read: "%s".' % (expectedObjectName, readObjectName)
        ParseTreeError.__init__(self, additional_info, reader)

class MissingDirOpenBracket(ParseTreeError):
    def __init__(self, reader):
        additional_info = 'Missing "}".'
        ParseTreeError.__init__(self, additional_info, reader)

class MissingStringOpenQuotMark(ParseTreeError):
    def __init__(self, reader):
        additional_info = "Missing opening '\"'."
        ParseTreeError.__init__(self, additional_info, reader)

class MissingStringCloseQuotMark(ParseTreeError):
    def __init__(self, reader):
        additional_info = "Missing closing '\"'."
        ParseTreeError.__init__(self, additional_info, reader)

class MissingEqualSign(ParseTreeError):
    def __init__(self, reader):
        additional_info = 'Missing "=".'
        ParseTreeError.__init__(self, additional_info, reader)

class InvalidPrimitive(ParseTreeError):
    def __init__(self, reader, primitiveTypeName):
        additional_info = 'Invalid data of type "%s".' % (primitiveTypeName)
        ParseTreeError.__init__(self, additional_info, reader)

class PrimitiveOutOfRange(ParseTreeError):
    def __init__(self, reader):
        additional_info = 'Data out of range.'
        ParseTreeError.__init__(self, additional_info, reader)

class DataRedefinition(ParseTreeError):
    def __init__(self, reader, tokenName):
        additional_info = 'Wrong keyword: "%s".' % (tokenName)
        ParseTreeError.__init__(self, additional_info, reader)

class UnknownKeyword(ParseTreeError):
    def __init__(self, reader, tokenName):
        additional_info = 'Wrong keyword: "%s".' % (tokenName)
        ParseTreeError.__init__(self, additional_info, reader)

class MissingDefault(ParseTreeError):
    def __init__(self, reader, tokenName):
        additional_info = 'No default value set for "%s".' % (tokenName)
        ParseTreeError.__init__(self, additional_info, reader)

class MissingDefaultSonDir(ParseTreeError):
    def __init__(self, reader):
        additional_info = 'No default son set.'
        ParseTreeError.__init__(self, additional_info, reader)

class ExclusionError(ParseTreeError):
    def __init__(self, reader, tokenName, presentTokenName):
        additional_info = '"%s" excludes "%s".' % (tokenName, presentTokenName)
        ParseTreeError.__init__(self, additional_info, reader)

class InclusionError(ParseTreeError):
    def __init__(self, reader, tokenName, presentTokenName):
        additional_info = '"%s" requires "%s".' % (tokenName, presentTokenName)
        ParseTreeError.__init__(self, additional_info, reader)
