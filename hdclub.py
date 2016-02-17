# coding: utf-8

import feedparser, filesystem
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
		self._dict['gold'] = False
		for span in self.soup.select('span'):
			try:
				text = span.get_text()
				if text == u'BDInfo Report':
					return False
				
				if text == u'Золотая раздача':
					self._dict['gold'] = True
				
				#print text.encode('utf-8')
				if tag == u'':
					tag = self.get_tag(text)
				else:
					self._dict[tag] = text.strip(' \t\n\r')
					tag = u''
			except:
				pass
				
		count_id = 0
		for a in self.soup.select('a'):
			try:
				href = a['href']
				components = href.split('/')
				if components[2] == u'www.imdb.com' and components[3] == u'title':
					self._dict['imdb_id'] = components[4]
					count_id += 1
				
				if self.settings:
					if self.settings.use_kinopoisk and components[2] == u'www.kinopoisk.ru':
						self._dict['kp_id'] = href

			except:
				pass
				
		if count_id > 1:
			return False
				
		for img in self.soup.select('img[src*="thumbnail.php"]'):
			try:
				self._dict['thumbnail'] = img['src']
				print self._dict['thumbnail']
			except:
				pass

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'))
				
		return True
		
def write_movie(item, settings):
	full_title = item.title
	print 'full_title: ' + full_title.encode('utf-8')

	parser = DescriptionParser(full_title, item.description, settings = settings)
	print '-------------------------------------------------------------------------'
	
	if parser.need_skipped(full_title):
		return
	
	if parser.parsed():
		filename = parser.make_filename()
		if not filename:
			return
		
		print 'filename: ' + filename.encode('utf-8')
		STRMWriter(item.link).write(filename, parser=parser, settings=settings)
		NFOWriter(parser, movie_api=parser.movie_api()).write_movie(filename)
		from downloader import TorrentDownloader
		TorrentDownloader(item.link, settings.addon_data_path, settings).download()
	else:
		skipped(item)
		
	del parser
		
def write_movies(content, path, settings):
	
	original_dir = filesystem.getcwd()
	
	if not filesystem.exists(path):
		filesystem.makedirs(path)
		
	filesystem.chdir(path)
	
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
		write_movie(item, settings)
			
	filesystem.chdir(original_dir)

def run(settings):
	if settings.animation_save:
		write_movies(settings.animation_url, settings.animation_path(), settings)
	if settings.documentary_save:
		write_movies(settings.documentary_url, settings.documentary_path(), settings)
	if settings.movies_save:
		write_movies(settings.movies_url, settings.movies_path(), settings)

def download_torrent(url, path, settings):
	url = url.replace('details.php', 'download.php')
	if not 'passkey' in url:
		url += '&passkey=' + settings.hdclub_passkey

	import shutil
	response = urllib2.urlopen(url)
	with filesystem.fopen(path, 'wb') as f:
		shutil.copyfileobj(response, f)
