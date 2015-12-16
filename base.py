# -*- coding: utf-8 -*-

import os, re, filesystem
from bs4 import BeautifulSoup
from settings import *
import urllib

KB = 1024
MB = KB * KB
GB = KB * MB

def make_fullpath(title, ext):
	return unicode(title.replace(':', '').replace('/', '#').replace('?', '') + ext)
	
def skipped(item):
	print item.title.encode('utf-8') + '\t\t\t[Skipped]'
	
def clean_html(page):
	#pattern = r"(?is)<script[^>]*>(.*?)</script>"
	#pattern = r'<script(.*?)</script>'
	#flags = re.M + re.S + re.I
	#r = re.compile(pattern, flags=flags)
	#print r
	#page = r.sub('', page)
	#print page.encode('utf-8')
	return page.replace("</sc'+'ript>", "").replace('</bo"+"dy>', '').replace('</ht"+"ml>', '')
	

def get_rank(full_title, parser, settings):
	
	preffered_size = 7 * GB
	#preffered_resolution_h = 1920
	preffered_resolution_v = 1080 if settings.preffered_type == QulityType.Q1080 else 720
	preffered_bitrate	= settings.preffered_bitrate
	
	print 'preffered_type: %s' % settings.preffered_type
	print 'preffered_bitrate: %d' % preffered_bitrate
	
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

	video = parser.get_value('video')
	for part in video.split(', '):
		multiplier = 0
		if 'kbps' in part \
			or 'kbs' in part \
			or 'Kbps' in part \
			or u'Кбит/сек' in part \
			or u'Кбит/с' in part \
			or 'Kb/s' in part \
			or '~' in part:
				multiplier = 1
		if 'mbps' in part \
			or 'mbs' in part \
			or 'Mbps' in part \
			or u'Мбит/сек' in part \
			or u'Mбит/с' in part \
			or u'Мбит/с' in part \
			or 'Mb/s' in part:
				multiplier = 1000
		if multiplier != 0:
			find = re.findall('[\d\.,]', part.split('(')[0])
			bitrate = ''.join(find).replace(',', '.')
			try:
				if bitrate != '' and float(bitrate) != 0 and float(bitrate) < 50000:
					print 'bitrate: %d kbps' % int(float(bitrate) * multiplier)
					if float(bitrate) * multiplier > preffered_bitrate:
						rank += float(bitrate) * multiplier / preffered_bitrate
					else:
						rank += preffered_bitrate / float(bitrate) * multiplier
					conditions += 1
				else:
					rank += 10
					conditions += 1
					print 'bitrate: not parsed'
			except:
				rank += 10
				conditions += 1
				print 'bitrate: not parsed'
		else:
			rank += 2
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
		if filesystem.isfile(fname_alt):
			with filesystem.fopen(fname_alt, "r") as alternative:
				s_alt = alternative.read().decode('utf-8')
	
		if not (link in s_alt):
			try:
				with filesystem.fopen(fname_alt, "a+") as alternative:
					alternative.write('#rank=' + str(rank) + '\n')
					alternative.write(link.encode('utf-8') + '\n')
			except:
				pass
				
	def get_link_with_min_rank(self, fname):
		fname_alt = fname + '.alternative'
		rank = 99999
		link = ''
		if filesystem.isfile(fname_alt):
			with filesystem.fopen(fname_alt, "r") as alternative:
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
		if filesystem.isfile(fname_alt):
			with filesystem.fopen(fname_alt, "r") as alternative:
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
		
	def fanart(self):
		if 'fanart' in self.dict:
			return self.dict['fanart']
		else:
			return None
		
	def __init__(self, content, settings = None):
		self.content = content
		html_doc = '<?xml version="1.0" encoding="UTF-8" ?>\n<html>' + content.encode('utf-8') + '\n</html>'
		self.soup = BeautifulSoup(clean_html(html_doc), 'html.parser')
		self.settings = settings
		self.OK = self.parse()
		
	def make_filename(self):
		filename = None
		try:
			title 			= self.dict['title']
			originaltitle 	= self.dict['originaltitle']
			
			if title == originaltitle:
				filename = title
			else:
				filename 		= title + ' # ' + originaltitle 
				
			filename 		+= ' (' + self.dict['year'] + ')'
		finally:
			return filename
			
	def need_skipped(self, full_title):
		
		for phrase in [u'[EN]', u'[EN / EN Sub]', u'[Фильмография]', u'[ISO]', u'DVD', u'стереопара', u'[Season', u'Half-SBS']:
			if phrase in full_title:
				print 'Skipped by: ' + phrase.encode('utf-8')
				return True
		
				
			if re.search('\(\d\d\d\d[-/]', full_title.encode('utf-8')):
				print 'Skipped by: Year'
				return True
		
		return False
		
		
		