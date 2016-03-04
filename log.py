try:
	from xbmc import log
except:
	def log(s):
		print s

prefix = 'script.media.aggregator'

def debug(s, line = None):
	if isinstance(s, unicode):
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
	
	