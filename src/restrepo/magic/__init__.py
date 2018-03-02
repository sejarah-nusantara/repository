#!/usr/bin/env python
# File downloaded from http://www.jsnp.net/code/magic.py
# and stripped down. Not installable from pypi apparently.
'''
magic.py
 determines a file type by its magic number

 (C)opyright 2000 Jason Petrone <jp_py@jsnp.net>
 All Rights Reserved

 Command Line Usage: running as `python magic.py file` will print
                     a description of what 'file' is.

 Module Usage:
     magic.whatis(data): when passed a string 'data' containing
                         binary or text data, a description of
                         what the data is will be returned.
'''

import struct

__version__ = '0.1'

magic = [
    [0L, 'string', '=', 'IIN1', 'image/tiff'],
    [0L, 'string', '=', 'MM\000*', 'image/tiff'],
    [0L, 'string', '=', 'II*\000', 'image/tiff'],
    [0L, 'string', '=', '\211PNG', 'image/x-png'],
    [1L, 'string', '=', 'PNG', 'image/x-png'],
    [0L, 'string', '=', 'GIF8', 'image/gif'],
    [0L, 'beshort', '=', 65496L, 'image/jpeg'],
    [0L, 'string', '=', 'hsi1', 'image/x-jpeg-proprietary'],
    [0L, 'string', '=', 'BM', 'image/x-bmp'],
]

magicNumbers = []


class magicTest:
    def __init__(self, offset, t, op, value, msg, mask=None):
        if t.count('&') > 0:
            mask = strToNum(t[t.index('&') + 1:])
            t = t[:t.index('&')]
        if isinstance(offset, type('a')):
            self.offset = strToNum(offset)
        else:
            self.offset = offset
        self.type = t
        self.msg = msg
        self.subTests = []
        self.op = op
        self.mask = mask
        self.value = value

    def test(self, data):
        if self.mask:
            data = data & self.mask
        if self.op == '=':
            if self.value == data:
                return self.msg
        elif self.op == '<':
            pass
        elif self.op == '>':
            pass
        elif self.op == '&':
            pass
        elif self.op == '^':
            pass
        return None

    def compare(self, data):
        #print str([self.type, self.value, self.msg])
        try:
            if self.type == 'string':
                c = ''
                s = ''
                for i in range(0, len(self.value) + 1):
                    if i + self.offset > len(data) - 1:
                        break
                    s = s + c
                    [c] = struct.unpack('c', data[self.offset + i])
                data = s
            elif self.type == 'short':
                [data] = struct.unpack('h', data[self.offset: self.offset + 2])
            elif self.type == 'leshort':
                [data] = struct.unpack('<h', data[self.offset: self.offset + 2])
            elif self.type == 'beshort':
                [data] = struct.unpack('>H', data[self.offset: self.offset + 2])
            elif self.type == 'long':
                [data] = struct.unpack('l', data[self.offset: self.offset + 4])
            elif self.type == 'lelong':
                [data] = struct.unpack('<l', data[self.offset: self.offset + 4])
            elif self.type == 'belong':
                [data] = struct.unpack('>l', data[self.offset: self.offset + 4])
            else:
                #print 'UNKNOWN TYPE: ' + self.type
                pass
        except:
            return None

#    print str([self.msg, self.value, data])
        return self.test(data)

def whatis(data):
    for test in magicNumbers:
        m = test.compare(data)
        if m:
            return m
    # no matching, magic number. is it binary or text?
    for c in data:
        if ord(c) > 128:
            return 'data'


def get_filetype(file):
    try:
        return whatis(open(file, 'r').read(8192))
    except Exception, e:
        if str(e) == '[Errno 21] Is a directory':
            return 'directory'
        else:
            raise e


#### BUILD DATA ####
#load('mime-magic')
#f = open('out', 'w')
#for m in magicNumbers:
#  f.write(str([m.offset, m.type, m.op, m.value, m.msg]) + ',\n')
#f.close

for m in magic:
    magicNumbers.append(magicTest(m[0], m[1], m[2], m[3], m[4]))
