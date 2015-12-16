# -*- coding: utf-8 -*-

import os, sys

__DEBUG__ = False

def get_filesystem_encoding():
	return sys.getfilesystemencoding() if os.name == 'nt' else 'utf-8'

def ensure_unicode(string, encoding=get_filesystem_encoding()):
	if isinstance(string, str):
		string = string.decode(encoding)
		
	if __DEBUG__:
		print '\tensure_unicode(%s, encoding=%s)' % (string.encode('utf-8'), encoding)
		
	return string
	
def get_path(path):
	errors='strict'
	path = ensure_unicode(path)
	return path.encode(get_filesystem_encoding(), errors)

def exists(path):
	return os.path.exists(get_path(path))
	
def getcwd():
	return ensure_unicode(os.getcwd(), get_filesystem_encoding())
	
def makedirs(path):
	os.makedirs(get_path(path))
	
def chdir(path):
	os.chdir(get_path(path))
	
def isfile(path):
	return os.path.isfile(get_path(path))
	
def abspath(path):
	return ensure_unicode(os.path.abspath(get_path(path)), get_filesystem_encoding())

def relpath(path, start=getcwd()):
	return ensure_unicode(os.path.relpath(get_path(path), get_path(start)), get_filesystem_encoding())
	
def fopen(path, mode):
	return open(get_path(path), mode)
	
def join(path, *paths):
	path = get_path(path)
	fpaths = []
	for p in paths:
		fpaths.append( get_path(p) )
	return ensure_unicode(os.path.join(path, *tuple(fpaths)), get_filesystem_encoding())
	
def test():	
	print 'Filesystem encoding: %s' % get_filesystem_encoding()
	print 'getcwd(): %s' % getcwd().encode('utf-8')
	print 'relpath(getcwd(), ".."): %s' % relpath(getcwd(), "..").encode('utf-8')
	
	subpath = u'Подпапка'
	subpath2 = u'файл.ext'
	fullpath = join(getcwd(), subpath, subpath2)
	
	print 'subpath: %s' % subpath.encode('utf-8')
	print 'subpath2: %s' % subpath2.encode('utf-8')
	print 'join(getcwd(), subpath, subpath2): %s' % fullpath.encode('utf-8')
	
	
if __name__ == '__main__':
	__DEBUG__ = True
	test()