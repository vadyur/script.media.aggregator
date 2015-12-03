# -*- coding: utf-8 -*-

import os
from bs4 import BeautifulSoup
import urllib

KB = 1024
MB = KB * KB
GB = KB * MB

def make_fullpath(title, ext):
	return title.replace(':', '').replace('/', '#').replace('?', '') + ext
def skipped(item):
	print item.title.encode('utf-8') + '\t\t\t[Skipped]'

def get_rank(full_title, parser):
	
	preffered_size = 7 * GB
	preffered_resolution_h = 1920
	preffered_resolution_v = 1080
	
	rank = 0.0
	conditions = 0
	
	if parser.get_value('gold'):
		rank += 0.8
		conditions += 1
		
	res_v = 1080
	if '720p' in full_title:
		res_v = 720
		
	if abs(preffered_resolution_v - res_v) > 0:
		rank += 2
		conditions += 1
		
	size = parser.get_value('size')
	if size != '':
		if int(size) > preffered_size:
			rank += int(size) / preffered_size
		else:
			rank += preffered_size / int(size)
		conditions += 1
		
	if parser.get_value('format') == 'MKV':
		rank += 0.6
		conditions += 1
		
	if 'ISO' in parser.get_value('format'):
		rank += 100
		conditions += 1
	
	if conditions != 0:
		return rank / conditions
	else:
		return 1
	
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
		
	@staticmethod
	def has_link(fname, link):
		fname_alt = fname + '.alternative'
		if os.path.isfile(fname_alt):
			with open(fname_alt, "r") as alternative:
				for line in alternative:
					if link in urllib.unquote(line):
						return True
		return False
				
	
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
		
		
		