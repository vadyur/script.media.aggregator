# -*- coding: utf-8 -*-

import os
from bs4 import BeautifulSoup

def make_fullpath(title, ext):
	return title.replace(':', '').replace('/', '#').replace('?', '') + ext
def skipped(item):
	print item.title.encode('utf-8') + '\t\t\t[Skipped]'

	
class STRMWriterBase:
	def make_alternative(self, fname, link, rank = 0):
		fname_alt = fname + '.alternative'
			
		s_alt = u''
		if os.path.isfile(fname_alt):
			with open(fname_alt, "r") as alternative:
				s_alt = alternative.read().decode('utf-8')
	
		if not (link in s_alt):
			with open(fname_alt, "a+") as alternative:
				alternative.write('#rank=' + str(rank) + '\n')
				alternative.write(link.encode('utf-8') + '\n')
				
	def get_link_with_min_rank(self, fname):
		fname_alt = fname + '.alternative'
		rank = 99999
		link = ''
		if os.path.isfile(fname_alt):
			with open(fname_alt, "r") as alternative:
				while True:
					line = alternative.readline()
					if not line:
						break
					line = line.decode('utf-8')
					if u'#rank=' in line:
						curr_rank = float(line.replace(u'#rank=', u''))
						if curr_rank < rank:
							rank = curr_rank
							line = alternative.readline()
							if not line:
								break
							line = line.decode('utf-8')
							link = line.replace(u'\r', u'').replace(u'\n', u'')
		return link
				
	
class DescriptionParserBase:
	dict = {}

	def Dump(self):
		print '-------------------------------------------------------------------------'
		for key, value in self.dict.iteritems():
			print key.encode('utf-8') + '\t: ' + value.encode('utf-8')
	
	def get_value(self, tag):
		try:
			return self.dict[tag]
		except:
			return u''

	def parsed(self):
		return self.OK

	def parse(self):	
		raise NotImplementedError("def parse(self): not imlemented.\nPlease Implement this method")
		
	def __init__(self, content):
		self.content = content
		html_doc = '<?xml version="1.0" encoding="UTF-8" ?>\n<html>' + content.encode('utf-8') + '\n</html>'
		self.soup = BeautifulSoup(html_doc, 'html.parser')
		self.OK = self.parse()
		
		
		