# -*- coding: utf-8 -*-

import log
from log import debug


import re
import urllib2, urlparse

from bs4 import BeautifulSoup

import base
import feedparser
import requests

import filesystem
from base import DescriptionParserBase, clean_html, Informer
from nfowriter import NFOWriter
from settings import Settings
from strmwriter import STRMWriter

import tvshowapi

def real_url(url, settings):
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult(res.scheme if res.scheme else 'http', settings.rutor_domain, res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	debug('real_url(%s, ...) return %s' % (url, res))
	return res


def origin_url(url, settings):
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult(res.scheme if res.scheme else 'http', 'rutor.info', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	debug('original_url(%s, ...) return %s' % (url, res))
	return res


class DescriptionParser(DescriptionParserBase):
	def __init__(self, content, settings=None):
		Informer.__init__(self)

		self._dict.clear()
		self.content = content
		self.settings = settings
		self.OK = self.parse()

	def get_tag(self, x):
		return {
			u'Название:': u'title',
			u'Оригинальное название:': u'originaltitle',
			u'Год выхода:': u'year',
			u'Жанр:': u'genre',
			u'Режиссер:': u'director',
			u'В ролях:': u'actor',
			u'О фильме:': u'plot',
			u'Продолжительность:': u'runtime',
			u'Качество:': u'format',
			#u'Производство:': u'country_studio',
			u'Страна:': u'country',
			u'Студия:': u'studio',
			u'Видео:': u'video',
			u'Перевод:': u'translate',
		}.get(x.strip(), u'')

	def clean(self, title):
		return title.strip(' \t\n\r')

	def get_title(self, full_title):
		try:
			sep = '/'
			if not ' / ' in full_title:
				sep = '\('

			found = re.search(r'^(.+?) ' + sep, full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title

	def get_original_title(self, full_title):
		if not ' / ' in full_title:
			return self.get_title(full_title)

		try:
			found = re.search(r'^.+? / (.+?) \(', full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title

	def get_year(self, full_title):
		try:
			found = re.search(r'\((\d+)\)', full_title).group(1)
			return unicode(found)
		except AttributeError:
			return 0

	def parse_title(self, full_title):
		self._dict['full_title'] = full_title
		self._dict['title'] = self.get_title(full_title)
		self._dict['originaltitle'] = self.get_original_title(full_title)
		self._dict['year'] = self.get_year(full_title)

	def parse_title_tvshow(self, full_title):
		self.parse_title(full_title)

	def parse(self):
		if True:
			try:
				self._link = self.content
				debug(self._link)
			except:
				return False

			full_title = self._dict['full_title']
			debug('full_title: ' + full_title.encode('utf-8'))

			self.parse_title(full_title)

			if self.need_skipped(full_title):
				return False

			r = requests.get(real_url(self._link, self.settings))
			if r.status_code == requests.codes.ok:
				return self.parse_description(r.text)

		return False

	def parse_description(self, html_text):
		from HTMLParser import HTMLParseError

		html_text = clean_html(html_text)
		try:
			self.soup = BeautifulSoup(html_text, 'html.parser')
		except HTMLParseError as e:
			log.print_tb(e)
			log.debug(html_text)
			return False

		tag = u''

		for b in self.soup.select('#details b'):
			try:
				text = b.get_text()
				tag = self.get_tag(text)
				if tag == 'plot':
					self._dict[tag] = base.striphtml(unicode(b.next_sibling.next_sibling).strip())
					debug('%s (%s): %s' % (text.encode('utf-8'), tag.encode('utf-8'), self._dict[tag].encode('utf-8')))
				elif tag == 'genre':
					genres = []
					elements = b.findNextSiblings('a')
					for a in elements:
						if '/tag/' in a['href']:
							genres.append(a.get_text())

					self._dict[tag] = u', '.join(genres)

				elif tag != '':
					self._dict[tag] = base.striphtml(unicode(b.next_sibling).strip())
					debug('%s (%s): %s' % (text.encode('utf-8'), tag.encode('utf-8'), self._dict[tag].encode('utf-8')))
			except:
				pass
		if 'genre' in self._dict:
			self._dict['genre'] = self._dict['genre'].lower().replace('.', '')

		count_id = 0
		for a in self.soup.select('a[href*="www.imdb.com/title/"]'):
			try:
				href = a['href']

				components = href.split('/')
				if components[2] == u'www.imdb.com' and components[3] == u'title':
					self._dict['imdb_id'] = components[4]
					count_id += 1
			except:
				pass

		if count_id == 0:
			div_index = self.soup.select('#index')
			if div_index:
				for a in div_index[0].findAll('a', recursive=True):
					if '/torrent/' in a['href']:
						parts = a['href'].split('/')
						href = parts[0] + '/' + parts[1] + '/' + parts[2]
						html = urllib2.urlopen(real_url(href, settings))
						soup = BeautifulSoup(clean_html(html.read()), 'html.parser')

						for a in soup.select('a[href*="www.imdb.com/title/"]'):
							try:
								href = a['href']

								components = href.split('/')
								if components[2] == u'www.imdb.com' and components[3] == u'title':
									self._dict['imdb_id'] = components[4]
									count_id += 1
							except:
								pass

					if 'imdb_id' in self._dict:
						break

		if count_id > 1:
			return False

		for det in self.soup.select('#details'):
			tr = det.find('tr', recursive=False)
			if tr:
				tds = tr.findAll('td', recursive=False)
				if len(tds) > 1:
					td = tds[1]
					img = td.find('img')
					try:
						self._dict['thumbnail'] = img['src']
						debug('!!!!!!!!!!!!!!thumbnail: ' + self._dict['thumbnail'])
						break
					except:
						pass

		if self.settings:
			if self.settings.use_kinopoisk:
				for kp_id in self.soup.select('a[href*="www.kinopoisk.ru/"]'):
					self._dict['kp_id'] = kp_id['href']

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'))

		return True

	def link(self):
		return origin_url(self._link, self.settings)

class DescriptionParserTVShows(DescriptionParser):

	def need_skipped(self, full_title):
		for phrase in [u'[EN]', u'[EN / EN Sub]', u'[Фильмография]', u'[ISO]', u'DVD', u'стереопара', u'Half-SBS']:
			if phrase in full_title:
				debug('Skipped by: ' + phrase.encode('utf-8'))
				return True
		return False


class DescriptionParserRSS(DescriptionParser):
	def __init__(self, title, link, settings=None):
		Informer.__init__(self)

		self._dict.clear()
		self.content = link
		self.settings = settings
		self._dict['full_title'] = title.strip(' \t\n\r')
		self.OK = self.parse()


class DescriptionParserRSSTVShows(DescriptionParserRSS, DescriptionParserTVShows):
	pass


def write_movie_rss(fulltitle, description, link, settings):
	parser = DescriptionParserRSS(fulltitle, link, settings)
	if parser.parsed():
		import movieapi
		movieapi.write_movie(fulltitle, link, settings, parser)


def write_tvshow(fulltitle, description, link, settings):
	parser = DescriptionParserRSSTVShows(fulltitle, link, settings)
	if parser.parsed():
		tvshowapi.write_tvshow(fulltitle, link, settings, parser)
		#save_download_link(parser, settings, link)


def title(rss_url):
	return 'rutor'

def is_tvshow(title):
	m = re.match(r'.+?\[.+?\] \(\d\d\d\d', title)
	if m:
		return True

	return False

def get_source_url(link):
	m = re.match(r'.+=(\d+)$', link)
	if m is None:
		return None
	return 'http://rutor.info/torrent/%s/' % m.group(1)

def write_tvshows(rss_url, path, settings):
	debug('------------------------- Rutor: %s -------------------------' % rss_url)

	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(real_url(rss_url, settings))

		cnt = 0
		settings.progress_dialog.update(0, title(rss_url), path)

		for item in d.entries:
			if not is_tvshow(item.title):
				continue

			try:
				debug(item.title.encode('utf-8'))
			except:
				continue

			write_tvshow(
				fulltitle=item.title,
				description=item.description,
				link=origin_url(get_source_url(item.link), settings),
				settings=settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), title(rss_url), path)


def write_movies_rss(rss_url, path, settings):

	debug('------------------------- Rutor Club: %s -------------------------' % rss_url)

	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(real_url(rss_url, settings))

		cnt = 0
		settings.progress_dialog.update(0, title(rss_url), path)

		for item in d.entries:
			if is_tvshow(item.title):
				continue

			try:
				debug(item.title.encode('utf-8'))
			except:
				continue
			write_movie_rss(
				fulltitle=item.title,
				description=item.description,
				link=origin_url(get_source_url(item.link), settings),
				settings=settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), title(rss_url), path)


def get_rss_url(f_id):
	return 'http://rutor.info/rss.php?cat=' + str(f_id)


#def get_fav_rss_url(f_id, passkey, uid):
#	return 'http://nnm-club.me/forum/rss2.php?f=' + str(f_id) + '&dl=' + str(uid) + '&t=1&uk=' + passkey + '&r'


def run(settings):
	if settings.movies_save:
		write_movies_rss(get_rss_url(1), settings.movies_path(), settings)

	if settings.animation_save:
		write_movies_rss(get_rss_url(7), settings.animation_path(), settings)

	if settings.animation_tvshows_save:
		write_tvshows(get_rss_url(7), settings.animation_tvshow_path(), settings)

	if settings.tvshows_save:
		write_tvshows(get_rss_url(4), settings.tvshow_path(), settings)


def get_magnet_link(url):
	r = requests.get(real_url(url, settings))
	if r.status_code == requests.codes.ok:
		soup = BeautifulSoup(clean_html(r.text), 'html.parser')
		for a in soup.select('a[href*="magnet:"]'):
			debug(a['href'])
			return a['href']
	return None


def download_torrent(url, path, settings):
	url = urllib2.unquote(url)
	debug('download_torrent:' + url)

	page = requests.get(real_url(url, settings))
	# debug(page.text.encode('cp1251'))

	soup = BeautifulSoup(clean_html(page.text), 'html.parser')
	a = soup.select('#download > a')
	if len(a) > 1:
		link = a[1]['href']
	else:
		link = None

	if link:
		#if not link.startswith('http'):
		#	link = 'http://' + settings.rutor_domain + link
		r = requests.get(real_url(link, settings))

	debug(r.headers)

	if 'Content-Type' in r.headers:
		if not 'torrent' in r.headers['Content-Type']:
			return False

	try:
		with filesystem.fopen(path, 'wb') as torr:
			for chunk in r.iter_content(100000):
				torr.write(chunk)
		return True
	except:
		pass

	return False


if __name__ == '__main__':
	settings = Settings('../../..')
	settings.addon_data_path = u"c:\\Users\\vd\\AppData\\Roaming\\Kodi\\userdata\\addon_data\\script.media.aggregator\\"
	settings.rutor_domain = 'rutor.is'
	run(settings)
