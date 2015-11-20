# coding: utf-8

import feedparser
import xml.etree.cElementTree as ET
from bs4 import BeautifulSoup
import urllib2
import json, os
from settings import Settings
from base import *
from movieapi import *
from nfowriter import *
from strmwriter import *

KB = 1024
MB = KB * KB
GB = KB * MB

class DescriptionParser(DescriptionParserBase):
				
	def get_tag(self, x):
		return {
			u'Название:': u'title',
			u'Оригинальное название:': u'originaltitle',
			u'Год выхода:': u'year',
			u'Жанр:': u'genre',
			u'Режиссер:': u'director',
			u'В ролях:': u'actor',
			u'Сюжет фильма:': u'plot',
			u'Продолжительность:': u'runtime',
			u'Формат:': u'format',
			u'Видео:': u'video',
		}.get(x, u'')
		
	def parse(self):
		#title - Название:
		tag = u''
		self.dict['gold'] = False
		for span in self.soup.select('span'):
			try:
				text = span.get_text()
				if text == u'BDInfo Report':
					return False
				
				if text == u'Золотая раздача':
					self.dict['gold'] = True
				
				#print text.encode('utf-8')
				if tag == u'':
					tag = self.get_tag(text)
				else:
					self.dict[tag] = text
					tag = u''
			except:
				pass
				
		for a in self.soup.select('a'):
			try:
				href = a['href']
				components = href.split('/')
				if components[2] == u'www.imdb.com' and components[3] == u'title':
					self.dict['imdb_id'] = components[4]
			except:
				pass
				
		for img in self.soup.select('img[src*="thumbnail.php"]'):
			try:
				self.dict['thumbnail'] = img['src']
				print self.dict['thumbnail']
			except:
				pass
			
				
		return True
		
		
def get_rank(item, parser):
	
	preffered_size = 7 * GB
	preffered_resolution_h = 1920
	preffered_resolution_v = 1080
	
	rank = 0.0
	conditions = 0
	
	if parser.get_value('gold'):
		rank += 0.8
		conditions += 1
		
	res_v = 1080
	if '720p' in item.title:
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
		
def write_movie(content, path):
	
	original_dir = os.getcwd()
	
	if not os.path.exists(path):
		os.makedirs(path)
		
	os.chdir(path)
	
	d = feedparser.parse(content)
	'''
	print d.feed.publisher
	print d.feed.subtitle
	print d.feed.language
	print d.feed.title.encode('utf-8')
	print d.entries[0].title.encode('utf-8')
	print d.entries[0].description.encode('utf-8')
	print d.entries[0].link
	'''
	for item in d.entries:
		parser = DescriptionParser(item.description)
		print '-------------------------------------------------------------------------'
		
		if parser.parsed():
			filename = parser.get_value('title') + ' # ' + parser.get_value('originaltitle') + ' (' + parser.get_value('year') + ')'
			
			print filename.encode('utf-8')
			STRMWriter(item).write(filename, rank = get_rank(item, parser))
			NFOWriter().write(parser, filename)
		else:
			skipped(item)
			
	os.chdir(original_dir)

def run(settings):
	write_movie(settings.animation_url, settings.animation_path())
	write_movie(settings.documentary_url, settings.documentary_path())
	write_movie(settings.movies_url, settings.movies_path())
