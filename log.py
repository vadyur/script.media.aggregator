try:
	from xbmc import log
except:
	def log(s):
		print s

import inspect

prefix = 'script.media.aggregator'

import sys
try:
	if len(sys.argv) > 1:
		handle = int(sys.argv[1])
		prefix += ': ' + sys.argv[1]
except:
	pass

def debug(s, line = None):

	if isinstance(s, BaseException):
		print_tb(s)
		return
	elif isinstance(s, unicode):
		s = s.encode('utf-8')
	elif not isinstance(s, str):
		s = str(s)

	if prefix:
		if line:
			message = '[%s: %s] %s' % (prefix, str(line), s)
		else:
			message = '[%s]  %s' % (prefix, s)
	else:
		if line:
			message = '[%s]  %s' % (line, s)
		else:
			message = s
			
	log(message)
	

def print_tb(e=None):
	import sys
	exc_type, exc_val, exc_tb = sys.exc_info()
	import traceback
	traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=sys.stderr)

	if e:
		debug(str(e))

def lineno():
	"""Returns the current line number in our program."""
	return inspect.currentframe().f_back.f_lineno

def fprint_tb(filename):
	import sys, filesystem
	exc_type, exc_val, exc_tb = sys.exc_info()
	import traceback

	with filesystem.fopen(filename, 'w') as out:
		traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=out)


class dump_context:
	def __init__(self, module, use_timestamp=True):
		self.module			= module
		self.use_timestamp	= use_timestamp

	def timestamp(self):
		if self.use_timestamp:
			import time
			return time.strftime('%Y%m%d_%H%M%S')
		else:
			return ''

	def filename(self):
		import filesystem
		name = self.module + self.timestamp() + '.log'
		try:
			from xbmc import translatePath
			_filename = 'special://logpath/' + name
		except ImportError:
			_filename = filesystem.abspath(filesystem.join( __file__ ,'../../..', name))
		return _filename

	def __enter__(self):
		fn = self.filename()

		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		if exc_type:
			import filesystem
			with filesystem.fopen(self.filename(), 'w') as out:
				import traceback
				traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=out)
			return True
