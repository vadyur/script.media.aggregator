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
				
				if self.settings:
					if self.settings.use_kinopoisk and components[2] == u'www.kinopoisk.ru':
						self.dict['kp_id'] = href

			except:
				pass
				
		for img in self.soup.select('img[src*="thumbnail.php"]'):
			try:
				self.dict['thumbnail'] = img['src']
				print self.dict['thumbnail']
			except:
				pass
			
				
		return True
		
def write_movies(content, path, settings):
	
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
		parser = DescriptionParser(item.description, settings = settings)
		print '-------------------------------------------------------------------------'
		
		if parser.parsed():
			filename = parser.get_value('title') + ' # ' + parser.get_value('originaltitle') + ' (' + parser.get_value('year') + ')'
			
			print filename.encode('utf-8')
			STRMWriter(item.link).write(filename, rank = get_rank(item.title, parser), settings = settings)
			NFOWriter().write(parser, filename)
		else:
			skipped(item)
			
	os.chdir(original_dir)

def run(settings):
	write_movies(settings.animation_url, settings.animation_path(), settings)
	write_movies(settings.documentary_url, settings.documentary_path(), settings)
	write_movies(settings.movies_url, settings.movies_path(), settings)

