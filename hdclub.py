# coding: utf-8

import log
from log import debug, print_tb


import feedparser, filesystem
#import xml.etree.cElementTree as ET
from bs4 import BeautifulSoup
import urllib2
import json, os
from settings import Settings
from base import *
from movieapi import *
from nfowriter import *
from strmwriter import *

def real_url(url):
	import urlparse
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult('https', 'elitehd.org', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	debug('real_url(%s, ...) return %s' % (url, res))
	return res


def origin_url(url):
	import urlparse
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult('http', 'hdclub.org', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	debug('original_url(%s, ...) return %s' % (url, res))
	return res


class DescriptionParser(DescriptionParserBase):

	def __init__(self, full_title, content, link, settings, imdb=None):
		self._link = link
		DescriptionParserBase.__init__(self, full_title, content, settings)
		if imdb:
			self._dict['imdb_id'] = imdb

	def link(self):
		return origin_url(self._link)

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
				
				if tag == u'':
					tag = self.get_tag(text.strip(' \t\n\r'))
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

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'), settings=self.settings)
				
		return True

def make_full_url(link):
	import urlparse
	res = urlparse.urlparse(link)
	res = urlparse.ParseResult(res.scheme if res.scheme else 'http', 'hdclub.org', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)

	return res
		
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
		STRMWriter(origin_url(item.link)).write(filename, parser=parser, settings=settings)
		NFOWriter(parser, movie_api=parser.movie_api()).write_movie(filename)
		from downloader import TorrentDownloader
		TorrentDownloader(item.link, settings.torrents_path(), settings).download()
	else:
		skipped(item)
		
	del parser
		
def write_movies(rss_url, path, settings):
	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(real_url(rss_url))

		cnt = 0
		settings.progress_dialog.update(0, 'elitehd', path)

		for item in d.entries:
			item.link = origin_url(item.link)
			write_movie(item, settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'elitehd', path)


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
		d = feedparser.parse(real_url(rss_url))

		cnt = 0
		settings.progress_dialog.update(0, 'elitehd', path)

		for item in d.entries:
			item.link = origin_url(item.link)
			write_tvshow(item, settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'elitehd', path)


def get_rss_url(f_id, passkey):
	return 'https://hdclub.org/rss.php?cat=' + str(f_id) + '&passkey=' + passkey


def run(settings):
	if settings.animation_save:
		write_movies(settings.animation_url, settings.animation_path(), settings)

	if settings.documentary_save:
		write_movies(settings.documentary_url, settings.documentary_path(), settings)

	if settings.movies_save:
		write_movies(settings.movies_url, settings.movies_path(), settings)

	if settings.tvshows_save:
		write_tvshows(get_rss_url(64, settings.hdclub_passkey), settings.tvshow_path(), settings)


def make_search_url(what, IDs, imdb, settings):
	url = u'https://hdclub.org/browse.php'   # ?c71=1&webdl=0&3d=0&search=%D2%EE%F0&incldead=0&dsearch=&stype=or'
	url += '?c=' + str(IDs)
	url += '&passkey=' + settings.hdclub_passkey
	if imdb is None:
		url += '&search=' + urllib2.quote(what.encode('cp1251'))
	url += '&dsearch=' + imdb
	return url


def search_generate(what, imdb, settings, path_out):

	return 0	# TODO login with captcha

	count = 0
	session = requests.session()

	if settings.movies_save:
		url = make_search_url(what, 71, imdb, settings)
		result1 = search_results(imdb, session, settings, url, 71)
		count += make_search_strms(result1, settings, 'movie', settings.movies_path(), path_out)

	if settings.animation_save and count == 0:
		url = make_search_url(what, 70, imdb, settings)
		result2 = search_results(imdb, session, settings, url, 70)
		count += make_search_strms(result2, settings, 'movie', settings.animation_path(), path_out)

	if settings.documentary_save and count == 0:
		url = make_search_url(what, 78, imdb, settings)
		result3 = search_results(imdb, session, settings, url, 78)
		count += make_search_strms(result3, settings, 'movie', settings.documentary_path(), path_out)

	if settings.tvshows_save and count == 0:
		url = make_search_url(what, 64, imdb, settings)
		result4 = search_results(imdb, session, settings, url, 64)
		count += make_search_strms(result4, settings, 'tvshow', settings.tvshow_path(), path_out)

	return count


def make_search_strms(result, settings, type, path, path_out):
	count = 0
	for item in result:
		link = item['link']
		parser = item['parser']
		if link:
			settings.progress_dialog.update(count * 100 / len(result), 'elitehd', parser.get_value('full_title'))

			if type == 'movie':
				import movieapi
				path = movieapi.write_movie(parser.get_value('full_title'), link, settings, parser, path, skip_nfo_exists=True)
				path_out.append(path)
				count += 1
			if type == 'tvshow':
				import tvshowapi
				path = tvshowapi.write_tvshow(parser.get_value('full_title'), link, settings, parser, path, skip_nfo_exists=True)
				path_out.append(path)
				count += 1

	return count


class TrackerPostsEnumerator(object):
	_items = []

	def __init__(self, session):
		self._s = session
		self._items[:] = []

	def items(self):
		return self._items

	def process_page(self, url):
		request = self._s.get(real_url(url))
		self.soup = BeautifulSoup(clean_html(request.text), 'html.parser')
		debug(url)

		# item = {}
		# item['category'] = cat_a['href']
		# item['a'] = topic_a
		# item['dl_link'] = dl_a['href']
		# item['seeds'] = seeds_td.get_text()
		# self._items.append(item.copy())

		tbody = self.soup.find('tbody', attrs={'id': 'highlighted'})
		if tbody:
			for tr in tbody:
				try:
					from bs4 import NavigableString
					if isinstance(tr, NavigableString):
						continue

					item = {}
					TDs = tr.find_all('td', recursive=False)
					item['a'] = TDs[2].find('a')['href']
					item['title'] = TDs[2].find('a').get_text().strip(' \n\r\t')
					item['dl_link'] = item['a'].replace('details.php', 'download.php')
					item['seeds'] = TDs[4].get_text().strip(' \n\r\t')
					item['cat'] = TDs[0].find('a')['href'].split('cat=')[-1]
					self._items.append(item.copy())
				except BaseException as e:
					log.print_tb(e)

def search_results(imdb, session, settings, url, cat):
	debug('search_results: url = ' + url)

	enumerator = TrackerPostsEnumerator(session)
	enumerator.process_page(url)
	result = []
	for post in enumerator.items():
		if 'seeds' in post and int(post['seeds']) < 5:
			continue

		if str(post.get('cat', '')) != str(cat):
			continue

		# full_title, content, link, settings

		page = requests.get(real_url(make_full_url(post['a'])))

		soup = BeautifulSoup(page.text, "html.parser")

		content = ''
		tbl = soup.find('table', class_='heading_b')

		for td in tbl.find_all('td', class_='heading_r'):
			content += td.prettify()

		img = soup.find('img', attrs = {'title': "IMDB"})
		if img:
			content += img.parent.prettify()

		img = soup.find('img', attrs = {'title': u"Кинопоиск"})
		if img:
			content += img.parent.prettify()

		parser = DescriptionParser(post['title'], content, make_full_url(post['a']), settings=settings, imdb=imdb)
		
		debug(u'%s %s %s' % (post['title'], str(parser.parsed()), parser.get_value('imdb_id')))
		if parser.parsed(): # and parser.get_value('imdb_id') == imdb:
			result.append({'parser': parser, 'link': make_full_url(post['dl_link'])})

	return result


def download_torrent(url, path, settings):
	from base import save_hashes
	save_hashes(path)
	url = url.replace('details.php', 'download.php')
	if not 'passkey' in url:
		url += '&passkey=' + settings.hdclub_passkey

	try:
		import shutil
		response = urllib2.urlopen(real_url(url))
		with filesystem.fopen(path, 'wb') as f:
			shutil.copyfileobj(response, f)
		save_hashes(path)
		return True
	except BaseException as e:
		print_tb(e)
		return False


