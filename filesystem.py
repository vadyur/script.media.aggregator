import os, sys

def get_filesystem_encoding():
	return sys.getfilesystemencoding() if os.name == 'nt' else 'utf-8'

def ensure_unicode(string, encoding='utf-8'):
	if isinstance(string, str):
		string = string.decode(encoding)
	return string
	
def get_path(path):
	errors='strict'
	path = ensure_unicode(path)
	return path.encode(get_filesystem_encoding(), errors)

def exists(path):
	return os.path.exists(get_path(path))
	
def getcwd():
	return os.getcwd()
	
def makedirs(path):
	os.makedirs(get_path(path))
	
def chdir(path):
	os.chdir(get_path(path))
	
def isfile(path):
	return os.path.isfile(get_path(path))
	
def abspath(path):
	return os.path.abspath(get_path(path))

def relpath(path, start=os.curdir):
	return os.path.relpath(get_path(path), get_path(start))