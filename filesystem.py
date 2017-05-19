# -*- coding: utf-8 -*-

import os, sys, log
try:
	import xbmc, xbmcvfs
except ImportError: pass

__DEBUG__ = False


class MakeCHDirException(Exception):
	def __init__(self, path):
		self.path = path


def get_filesystem_encoding():
	return sys.getfilesystemencoding() if os.name == 'nt' else 'utf-8'


def ensure_unicode(string, encoding=get_filesystem_encoding()):
	if isinstance(string, str):
		string = string.decode(encoding)
		
	if __DEBUG__:
		log.debug('\tensure_unicode(%s, encoding=%s)' % (string.encode('utf-8'), encoding))
		
	return string

_cwd = ensure_unicode(os.getcwd(), get_filesystem_encoding())


def get_path(path):
	errors='strict'

	if path.startswith('smb://') and os.name == 'nt':
		path = path.replace('smb://', r'\\').replace('/', '\\')

	path = ensure_unicode(path)

	if os.name == 'nt':
		return path
	return path.encode(get_filesystem_encoding(), errors)


def _is_abs_path(path):
	if path.startswith('/'):
		return True

	if '://' in path:
		return True

	if os.name == 'nt':
		import re
		if re.match(r"[a-zA-Z]:", path):
			return True

		if path.startswith(r'\\'):
			return True

	return False

def xbmcvfs_path(path):
	if isinstance(path, unicode):
		u8path = path.encode('utf-8')

	if _is_abs_path(path):
		return xbmc.translatePath(u8path)
	else:
		return xbmc.translatePath(os.path.join(_cwd.encode('utf-8'), u8path))

def exists(path):
	try:
		return xbmcvfs.exists(xbmcvfs_path(path))
	except BaseException as e:
		return os.path.exists(get_path(path))


def getcwd():
	if '://' in _cwd:
		return _cwd
	else:
		return ensure_unicode(os.getcwd(), get_filesystem_encoding())


def makedirs(path):
	try:
		return xbmcvfs.mkdirs(xbmcvfs_path(path))
	except ImportError:
		os.makedirs(get_path(path))


def chdir(path):
	global _cwd
	_cwd = path

	try:
		path = xbmcvfs_path(path).decode('utf-8')
	except: pass

	try:
		os.chdir(get_path(path))
	except: pass


def save_make_chdir(new_path):
	current = getcwd()
	try:
		if not exists(new_path):
			makedirs(new_path)
		chdir(new_path)
	except BaseException as e:
		log.print_tb(e)
		raise MakeCHDirException(current)
	finally:
		return current


class save_make_chdir_context(object):

	def __init__(self, path):
		self.newPath = path

	# context management
	def __enter__(self):
		self.savePath = getcwd()
		if not exists(self.newPath):
			makedirs(self.newPath)
		chdir(self.newPath)

		log.debug(u'save_make_chdir_context: enter to %s from %s' % (self.newPath, self.savePath))

		return self

	def __exit__(self, exc_type, exc_val, exc_tb):

		log.debug(u'save_make_chdir_context: exit from %s to %s' % (getcwd(), self.savePath))

		chdir(self.savePath)
		if exc_type:
			import traceback
			traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=sys.stderr)
			log.debug("!!error!! " + str(exc_val))
			return True


def isfile(path):
	if not exists(path):
		return False
		#raise Exception('sfile.isFile error %s does not exists' % path)

	try:
		import stat
		return stat.S_ISREG(xbmcvfs.Stat(xbmcvfs_path(path)).st_mode())
	except ImportError:
		return os.path.isfile(get_path(path))


def abspath(path):
	if '://' in path:
		return path
	return ensure_unicode(os.path.abspath(get_path(path)), get_filesystem_encoding())


def relpath(path, start=getcwd()):
	return ensure_unicode(os.path.relpath(get_path(path), get_path(start)), get_filesystem_encoding())


def normpath(path):
	return ensure_unicode(os.path.normpath(get_path(path)), get_filesystem_encoding())

	
def fopen(path, mode):
	try:
		from StringIO import StringIO
		class File(StringIO):
			def __enter__(self):
				return self

			def __exit__(self, exc_type, exc_val, exc_tb):
				self.close()

				if exc_type:
					import traceback
					traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=sys.stderr)
					log.debug("!!error!! " + str(exc_val))
					return True

			def __init__(self, filename, opt=''):
				self.opt = opt
				buf = ''

				self.filename = xbmcvfs_path(filename)
				if 'r' in opt or 'a+' in opt:
					exst = exists(filename)
					if not exst and 'r' in opt:
						from errno import ENOENT
						raise IOError(ENOENT, 'Not a file', filename)

					if exst:
						# read
						f = xbmcvfs.File(self.filename)
						buf = f.read()
						f.close()

				StringIO.__init__(self, buf)


			def close(self):
				if 'w' in self.opt or 'a' in self.opt:
					if not self.closed:
						f = xbmcvfs.File(self.filename, 'w')
						f.write(self.getvalue())
						f.close()

				StringIO.close(self)

			def size(self):
				return self.len

		if 'w' in mode:
			return File(path, 'w')
		else:
			return File(path)

	except BaseException:
		return open(get_path(path), mode)

	
def join(path, *paths):
	path = get_path(path)
	fpaths = []
	for p in paths:
		fpaths.append( get_path(p) )
	return ensure_unicode(os.path.join(path, *tuple(fpaths)), get_filesystem_encoding())


def listdir(path):
	ld = []
	try:
		dirs, files = xbmcvfs.listdir(xbmcvfs_path(path))
		for d in dirs:
			ld.append(d.decode('utf-8'))
		for f in files:
			ld.append(f.decode('utf-8'))
	except:
		path = get_path(path)
		if path.startswith(r'\\'):
			with save_make_chdir_context(path):
				for p in os.listdir('.'):
					ld.append(ensure_unicode(p))
		else:
			for p in os.listdir(path):
				ld.append(ensure_unicode(p))

	return ld


def remove(path):
	try:
		xbmcvfs.delete(xbmcvfs_path(path))
	except:
		os.remove(get_path(path))


def copyfile(src, dst):
	try:
		xbmcvfs.copy(xbmcvfs_path(src), xbmcvfs_path(dst))
	except:
		import shutil
		shutil.copyfile(get_path(src), get_path(dst))


def movefile(src, dst):
	try:
		xbmcvfs.rename(xbmcvfs_path(src), xbmcvfs_path(dst))
	except:
		import shutil
		shutil.move(get_path(src), get_path(dst))


def getmtime(path):
	try:
		import stat
		return stat.S_ISREG(xbmcvfs.Stat(xbmcvfs_path(path)).st_mtime())
	except ImportError:
		return os.path.getmtime(get_path(path))


def getctime(path):
	try:
		import stat
		return stat.S_ISREG(xbmcvfs.Stat(xbmcvfs_path(path)).st_ctime())
	except ImportError:
		return os.path.getctime(get_path(path))


def dirname(path):
	return ensure_unicode(os.path.dirname(get_path(path)))


def basename(path):
	return ensure_unicode(os.path.basename(get_path(path)))


def test():	
	log.debug('Filesystem encoding: %s' % get_filesystem_encoding())
	log.debug('getcwd(): %s' % getcwd().encode('utf-8'))
	log.debug('relpath(getcwd(), ".."): %s' % relpath(getcwd(), "..").encode('utf-8'))
	
	subpath = u'Подпапка'
	subpath2 = u'файл.ext'

	with save_make_chdir_context(join('special://temp', subpath)):
		log.debug('aaaaa')
		#raise Exception('save_make_chdir')
		#log.debug('bbbbb')
	
	fullpath = join(getcwd(), subpath, subpath2)
	log.debug('subpath: %s' % subpath.encode('utf-8'))
	log.debug('subpath2: %s' % subpath2.encode('utf-8'))
	log.debug('join(getcwd(), subpath, subpath2): %s' % fullpath.encode('utf-8'))

	log.debug(u'dirname(%s): %s' % (fullpath, dirname(fullpath)))

	remote_file = u'smb://192.168.21.33/Incoming/test.txt'
	if isfile(remote_file):
		with fopen(remote_file, "r") as f:
			log.debug(f.read())


if __name__ == '__main__':
	__DEBUG__ = True
	test()