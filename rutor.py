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

		self._dict = dict()
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
			u'Режиссёр:': u'director',
			u'В ролях:': u'actor',
			u'О фильме:': u'plot',
			u'Описание:': u'plot',
			u'Описание фильма:': u'plot',
			u'Сюжет фильма:': u'plot',
			u'Продолжительность:': u'runtime',
			u'Качество:': u'format',
			#u'Производство:': u'country_studio',
			u'Страна:': u'country',
			u'Студия:': u'studio',
			u'Видео:': u'video',
			u'Перевод:': u'translate',
		}.get(x.strip(), u'')

	def clean(self, title):
		title = re.sub('\[.+\]', '', title)
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

			if self.need_skipped_by_filter(full_title, self.settings.rutor_filter):
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
					plot = base.striphtml(unicode(b.next_sibling.next_sibling).strip())
					if plot:
						self._dict[tag] = plot
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

		tags = []
		for tag in [u'title', u'year', u'genre', u'director', u'actor', u'plot']:
			if tag not in self._dict:
				tags.append(tag)

		if tags:
			try:
				details = self.soup.select_one('#details').get_text()
				lines = details.split('\n')
				for l in lines:
					if ':' in l:
						key, desc = l.split(':', 1)
						key = key.strip(u' \r\n\t✦═')
						desc = desc.strip(u' \r\n\t')

						tag = self.get_tag(key+':')
						if tag and desc and tag not in self._dict:
							self._dict[tag] = desc
			except BaseException as e:
				debug('No parse #details')
				debug(e)
				pass

		if 'genre' in self._dict:
			self._dict['genre'] = self._dict['genre'].lower().replace('.', '')

		if 'video' in self._dict:
			self._dict['video'] = self._dict['video'].replace('|', ',')

			if self.settings.rutor_nosd:
				video = self._dict['video']
				parts = video.split(',')

				for part in parts:
					part = part.strip()

					if 'XviD' in part:
						return False

					m = re.search(ur'(\d+)[xXхХ](\d+)', part)
					if m:
						w = int(m.group(1))
						#h = int(m.group(2))
						if w < 1280:
							return False
		else:
			pass
			
		
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
						html = urllib2.urlopen(real_url(href, self.settings))
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

		if 'imdb_id' not in self._dict:
			if not hasattr(self.settings, 'no_skip_by_imdb'):
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

		for kp_id in self.soup.select('a[href*="www.kinopoisk.ru/"]'):
			self._dict['kp_id'] = kp_id['href']

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'), self.settings)

		return True

	def link(self):
		return origin_url(self._link, self.settings)

	def need_skipped_by_filter(self, full_title, rutor_filter):
		keywords = rutor_filter.split()
		m = re.search(r'\d+\)(.+?)\|', full_title)
		if m:
			quality_str = m.group(1)
			for key in keywords:
				if key in quality_str:
					return True

			return False

		return True


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

		self._dict = dict()
		self.content = link
		self.settings = settings
		self._dict['full_title'] = title.strip(' \t\n\r')
		self.OK = self.parse()


class DescriptionParserRSSTVShows(DescriptionParserRSS, DescriptionParserTVShows):
	pass


def write_movie_rss(fulltitle, description, link, settings, path):
	parser = DescriptionParserRSS(fulltitle, link, settings)
	if parser.parsed():
		import movieapi
		movieapi.write_movie(fulltitle, link, settings, parser, path=path, skip_nfo_exists=True)


def write_tvshow(fulltitle, description, link, settings, path):
	parser = DescriptionParserRSSTVShows(fulltitle, link, settings)
	if parser.parsed():
		tvshowapi.write_tvshow(fulltitle, link, settings, parser, path, skip_nfo_exists=True)
		#save_download_link(parser, settings, link)


def title(rss_url):
	return 'rutor'

def is_tvshow(title):
	m = re.match(r'.+?\[.+?\] \(\d\d\d\d', title)
	if m:
		return True

	m = re.search(r'\[[Ss]\d', title)
	if m:
		return True

	return False

def get_source_url(link):
	m = re.match(r'.+[=/](\d+)$', link)
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
				settings=settings,
				path=path)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), title(rss_url), path)


def write_movies_rss(rss_url, path, settings):

	debug('------------------------- Rutor: %s -------------------------' % rss_url)

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
				settings=settings,
				path=path)

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
	from base import save_hashes
	save_hashes(path)

	url = urllib2.unquote(url)
	debug('download_torrent:' + url)

	page = requests.get(real_url(url, settings))

	soup = BeautifulSoup(clean_html(page.text), 'html.parser')
	a = soup.select('#download > a')
	if len(a) > 1:
		link = a[1]['href']
	else:
		link = None

	if link:
		r = requests.get(real_url(link, settings))

		debug(r.headers)

		if 'Content-Type' in r.headers:
			if not 'torrent' in r.headers['Content-Type']:
				return False

		try:
			with filesystem.fopen(path, 'wb') as torr:
				for chunk in r.iter_content(100000):
					torr.write(chunk)

			save_hashes(path)
			return True
		except:
			pass

	return False


def make_search_strms(result, settings, type, path, path_out):
	count = 0
	for item in result:

		link = item['link']
		parser = item['parser']

		settings.progress_dialog.update(count * 100 / len(result), 'Rutor', parser.get_value('full_title'))

		if link:
			if type == 'movie':
				import movieapi
				_path = movieapi.write_movie(parser.get_value('full_title'), link, settings, parser, path, skip_nfo_exists=True)
				if _path:
					path_out.append(_path)
					count += 1
			if type == 'tvshow':
				import tvshowapi
				_path = tvshowapi.write_tvshow(parser.get_value('full_title'), link, settings, parser, path, skip_nfo_exists=True)
				if _path:
					path_out.append(_path)
					count += 1

	return count

class PostsEnumerator(object):
	# ==============================================================================================
	_items = []

	def __init__(self, settings):
		self._s = requests.Session()
		self.settings = settings
		self._items[:] = []

	def process_page(self, url):

		try:
			request = self._s.get(real_url(url, self.settings))
		except requests.exceptions.ConnectionError:
			return

		self.soup = BeautifulSoup(clean_html(request.text), 'html.parser')
		debug(url)

		indx = self.soup.find('div', attrs={'id': 'index'})
		if indx:
			bgnd = indx.find('tr', class_='backgr')
			if bgnd:
				for row in bgnd.next_siblings:
					td2 = row.contents[1]
					td5 = row.contents[-1]

					item = {}
					topic_a = td2.find_all('a')
					if topic_a:
						topic_a = topic_a[-1]
						item['a'] = topic_a

					dl_a = td2.find('a', class_='downgif')
					if dl_a:
						item['dl_link'] = dl_a['href']

					span_green = td5.find('span', class_='green')
					if span_green:
						item['seeds'] = span_green.get_text().strip()

					self._items.append(item.copy())


	def items(self):
		return self._items


def search_results(imdb, settings, url, what=None):
	result = []

	enumerator = PostsEnumerator(settings)

	from log import dump_context
	with dump_context('rutor.enumerator.process_page'):
		enumerator.process_page(url)

	for post in enumerator.items():
		try:
			if 'seeds' in post and int(post['seeds']) < 1:
				continue
		except ValueError:
			pass

		title = post['a'].get_text()
		dl_link = str('http://rutor.info' + post['dl_link'])
		link = get_source_url(dl_link)

		import copy
		s = copy.copy(settings)
		if not imdb:
			s.no_skip_by_imdb = True

		if is_tvshow(title):
			parser = DescriptionParserRSSTVShows(title, link, s)	#parser = DescriptionParser(post['a'], settings=settings, tracker=True)
		else:
			parser = DescriptionParserRSS(title, link, s)
		if parser.parsed():
			if (imdb and parser.get_value('imdb_id') == imdb):
				result.append({'parser': parser, 'link': dl_link})
			elif what and parser.Dict().get('title') == what:
				result.append({'parser': parser, 'link': dl_link})

	return result


def search_generate(what, imdb, settings, path_out):
	count = 0

	if settings.movies_save:
		url = 'http://rutor.info/search/0/1/010/2/' + imdb
		result1 = search_results(imdb, settings, url)
		count += make_search_strms(result1, settings, 'movie', settings.movies_path(), path_out)

	if settings.animation_save and count == 0:
		url = 'http://rutor.info/search/0/7/010/2/' + imdb
		result2 = search_results(imdb, settings, url)
		count += make_search_strms(result2, settings, 'movie', settings.animation_path(), path_out)

	if settings.animation_tvshows_save and count == 0:
		url = 'http://rutor.info/search/0/7/010/2/' + imdb
		result3 = search_results(imdb, settings, url)
		count += make_search_strms(result3, settings, 'tvshow', settings.animation_tvshow_path(), path_out)

	if settings.tvshows_save and count == 0:
		url = 'http://rutor.info/search/0/4/010/2/' + imdb
		result4 = search_results(imdb, settings, url)
		count += make_search_strms(result4, settings, 'tvshow', settings.tvshow_path(), path_out)

	if settings.movies_save and count == 0:
		# 0/5/000/0 - Наше кино, поиск по названию в разделе
		if not result1:
			url = 'http://rutor.info/search/0/5/000/0/' + urllib2.quote(what.encode('utf-8'))
			result1 = search_results(None, settings, url, what)
			count += make_search_strms(result1, settings, 'movie', settings.movies_path(), path_out)

	"""
		if not result4:
			url = 'http://rutor.info/search/0/4/000/0/' + urllib2.quote(what.encode('utf-8'))
			result4 = search_results(None, settings, url, what)
			with filesystem.save_make_chdir_context(settings.tvshow_path()):
				count += make_search_strms(result4, settings, 'tvshow', path_out)
	"""

	return count

if __name__ == '__main__':
	settings = Settings(r'c:\Users\vd\Videos')
	settings.addon_data_path = u"c:\\Users\\vd\\AppData\\Roaming\\Kodi\\userdata\\addon_data\\script.media.aggregator\\"
	settings.rutor_domain = 'new-rutor.org'
	settings.torrent_path = u'c:\\Users\\vd\\AppData\\Roaming\\Kodi\\userdata\\addon_data\\script.media.aggregator'
	settings.torrent_player = 'torrent2http'
	settings.kp_googlecache = True
	settings.kp_usezaborona = True
	settings.use_kinopoisk = False
	settings.use_worldart = True

	path_out = []
	#search_generate(u'Ольга', 'tt6481562', settings, path_out)

	#import time
	#from_time = time.time()

	#from backgrounds import recheck_torrent_if_need

	from log import dump_context
	with dump_context('rutor.run'):
		run(settings)

	#recheck_torrent_if_need(from_time, settings)

	#search_generate(None, 'tt2948356', settings)
