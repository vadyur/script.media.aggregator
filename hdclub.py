# coding: utf-8

import log
from log import debug, print_tb


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

	def __init__(self, full_title, content, link, settings):
		self._link = link
		DescriptionParserBase.__init__(self, full_title, content, settings)

	def link(self):
		return self._link

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
			u'Выпущено:': u'country_studio'
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
				
				#debug(text.encode('utf-8'))
				if tag == u'':
					tag = self.get_tag(text)
				else:
					self._dict[tag] = text.strip(' \t\n\r')
					tag = u''
			except:
				pass

		self.parse_country_studio()

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
				debug(self._dict['thumbnail'])
			except:
				pass

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'))
				
		return True
		
def write_movie(item, settings):
	full_title = item.title
	debug('full_title: ' + full_title.encode('utf-8'))

	parser = DescriptionParser(full_title, item.description, item.link,	settings)
	debug('-------------------------------------------------------------------------')
	
	if parser.need_skipped(full_title):
		return
	
	if parser.parsed():
		filename = parser.make_filename()
		if not filename:
			return
		
		debug('filename: ' + filename.encode('utf-8'))
		STRMWriter(item.link).write(filename, parser=parser, settings=settings)
		NFOWriter(parser, movie_api=parser.movie_api()).write_movie(filename)
		from downloader import TorrentDownloader
		TorrentDownloader(item.link, settings.torrents_path(), settings).download()
	else:
		skipped(item)
		
	del parser
		
def write_movies(rss_url, path, settings):
	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(rss_url)

		cnt = 0
		settings.progress_dialog.update(0, 'hdclub', path)

		for item in d.entries:
			write_movie(item, settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'hdclub', path)


def write_tvshow(item, settings):
	full_title = item.title
	debug('full_title: ' + full_title.encode('utf-8'))

	parser = DescriptionParser(full_title, item.description, item.link, settings)
	debug('-------------------------------------------------------------------------')

	if parser.need_skipped(full_title):
		return

	if parser.parsed():
		import tvshowapi
		tvshowapi.write_tvshow(full_title, item.link, settings, parser)

	del parser

def write_tvshows(rss_url, path, settings):

	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(rss_url)

		cnt = 0
		settings.progress_dialog.update(0, 'hdclub', path)

		for item in d.entries:
			write_tvshow(item, settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'hdclub', path)


def get_rss_url(f_id, passkey):
	return 'http://hdclub.org/rss.php?cat=' + str(f_id) + '&passkey=' + passkey

def run(settings):
	if settings.animation_save:
		write_movies(settings.animation_url, settings.animation_path(), settings)

	if settings.documentary_save:
		write_movies(settings.documentary_url, settings.documentary_path(), settings)

	if settings.movies_save:
		write_movies(settings.movies_url, settings.movies_path(), settings)

	if settings.tvshows_save:
		write_tvshows(get_rss_url(64, settings.hdclub_passkey), settings.tvshow_path(), settings)


def search(what, imdb, settings, type):
	if settings.movies_save and type == 'movie':
		pass


def download_torrent(url, path, settings):
	url = url.replace('details.php', 'download.php')
	if not 'passkey' in url:
		url += '&passkey=' + settings.hdclub_passkey

	try:
		import shutil
		response = urllib2.urlopen(url)
		with filesystem.fopen(path, 'wb') as f:
			shutil.copyfileobj(response, f)
		return True
	except BaseException as e:
		print_tb(e)
		return False