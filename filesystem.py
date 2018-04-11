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

def test_path(path):
	if not _is_abs_path(path):
		pass
	return path

def _get_path(path, use_unc_path=True):
	errors='strict'

	try:
		import xbmcvfs
	except ImportError:
		if path.startswith('smb://') and os.name == 'nt' and use_unc_path:
			path = path.replace('smb://', r'\\').replace('/', '\\')

	path = ensure_unicode(path)

	if os.name == 'nt':
		return path
	return path.encode(get_filesystem_encoding(), errors)

def get_path(path):
	return test_path(_get_path(path))


def xbmcvfs_path(path):
	if isinstance(path, unicode):
		u8path = path.encode('utf-8')
	else:
		u8path = path

	if _is_abs_path(path):
		return xbmc.translatePath(u8path)
	else:
		return xbmc.translatePath(os.path.join(_cwd.encode('utf-8'), u8path))

def exists(path):
	try:
		if '://' in path or ( not _is_abs_path(path) and '://' in _cwd ):
			import stat
			if stat.S_ISDIR(xbmcvfs.Stat(xbmcvfs_path(path)).st_mode()):
				return True

			return xbmcvfs.exists(xbmcvfs_path(path))
		else:
			return os.path.exists(get_path(path))
	except BaseException as e:
		return os.path.exists(get_path(path))


def getcwd():
	if '://' in _cwd:
		return _cwd
	else:
		try:
			return ensure_unicode(os.getcwd(), get_filesystem_encoding())
		except OSError:
			return _cwd


def makedirs(path):
	try:
		return xbmcvfs.mkdirs(xbmcvfs_path(path))
	except (ImportError, NameError):
		os.makedirs(get_path(path))


def chdir(path):
	global _cwd

	if not _is_abs_path(path):
		path = join(_cwd, path)

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


from log import dump_context
class save_make_chdir_context(dump_context):

	def __init__(self, path, module='save_make_chdir_context', use_timestamp=True):
		self.newPath = path
		dump_context.__init__(self, module, use_timestamp)

	# context management
	def __enter__(self):
		if not exists(self.newPath):
			makedirs(self.newPath)

		return dump_context.__enter__(self)

	# __exit__ in dump_context


def isfile(path):
	if not exists(path):
		return False
		#raise Exception('sfile.isFile error %s does not exists' % path)

	try:
		import stat
		return stat.S_ISREG(xbmcvfs.Stat(xbmcvfs_path(path)).st_mode())
	except (ImportError, NameError):
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
		import xbmcvfs

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
				if 'r' in opt or 'a' in opt:
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

				if 'a' in opt:
					self.seek(0, mode=2)

			def write(self, s):
				if not s: return

				if not isinstance(s, str):
					s = str(s)

				StringIO.write(self, s)


			def close(self):
				if 'w' in self.opt or 'a' in self.opt or '+' in self.opt:
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
			return File(path, mode)

	except BaseException:
		return open(get_path(path), mode)

	
def join(path, *paths):
	path = _get_path(path, use_unc_path=False)
	fpaths = []
	for p in paths:
		fpaths.append( _get_path(p) )
	res = ensure_unicode(os.path.join(path, *tuple(fpaths)), get_filesystem_encoding())
	if '://' in res:
		res = res.replace('\\', '/')
	return test_path(res)


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
		return xbmcvfs.Stat(xbmcvfs_path(path)).st_mtime()
	except (ImportError, NameError):
		return os.path.getmtime(get_path(path))


def getctime(path):
	try:
		import stat
		return xbmcvfs.Stat(xbmcvfs_path(path)).st_ctime()
	except (ImportError, NameError):
		return os.path.getctime(get_path(path))


def dirname(path):
	return ensure_unicode(os.path.dirname(_get_path(path, use_unc_path=False)))


def basename(path):
	return ensure_unicode(os.path.basename(_get_path(path, use_unc_path=False)))


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