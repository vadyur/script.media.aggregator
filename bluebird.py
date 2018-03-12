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

# http://bluebird-hd.org

def real_url(url):
	import urlparse
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult('http', 'bluebird-hd.org', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	#debug('real_url(%s, ...) return %s' % (url, res))
	return res


def origin_url(url):
	import urlparse
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult('http', 'bluebird-hd.org', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	#debug('original_url(%s, ...) return %s' % (url, res))
	return res


class DescriptionParser(DescriptionParserBase):

	def __init__(self, full_title, content, link, settings, imdb=None):
		self._link = link
		DescriptionParserBase.__init__(self, full_title, content, settings)
		if imdb:
			self._dict['imdb_id'] = imdb

	def need_skipped(self, full_title):
		if self.settings.bluebird_nouhd and 'UHD' in full_title.split(' '):
			return True

		return DescriptionParserBase.need_skipped(self, full_title)

	def link(self):
		return origin_url(self._link)

	def get_tag(self, x):
		return {
			u'Название': u'title',
			u'Оригинальное название': u'originaltitle',
			u'Год выхода': u'year',
			u'Жанр': u'genre',
			u'Режиссер': u'director',
			u'В ролях': u'actor',
			u'О фильме': u'plot',
			u'Продолжительность': u'runtime',
			u'Формат': u'format',
			u'Видео': u'video',
			u'Выпущено': u'country_studio'
		}.get(x.rstrip(':'), u'')

	def parse(self):
		#title - Название:
		tag = u''

		def get_actors(b):
			div = b.find_next('div')
			actors = []
			for img in div.find_all('img'):
				if 'sm_actor' in img['src']:
					actors.append(img['title'])
			if actors:
				return ', '.join(actors)

			txt = b.next_sibling
			from bs4 import NavigableString
			if isinstance(txt, NavigableString):
				txt = unicode(txt)
				if txt.startswith(':'):
					return txt.lstrip(':').strip()
				return txt if txt else ''
			return ''

		def get_other(b):
			return unicode(b.next_sibling).lstrip(':').strip()

		for b in self.soup.find_all('b'):
			tag = self.get_tag(b.get_text())
			if tag == 'actor':
				self.Dict()[tag] = get_actors(b)
			elif tag:
				self.Dict()[tag] = get_other(b)

		self.parse_country_studio()

		from sets import Set
		imdb_ids = Set()
		for a in self.soup.select('a'):
			try:
				href = a['href']
				components = href.split('/')
				if components[2] == u'www.imdb.com' and components[3] == u'title':
					imdb_ids.add(components[4])
				
				if components[2] == u'www.kinopoisk.ru' and 'film' in components:
					self._dict['kp_id'] = href

			except:
				pass

		if len(imdb_ids) > 1:
			return False
		elif len(imdb_ids) == 1:
			self._dict['imdb_id'] = imdb_ids.pop()

		s = origin_url('/torrents/images/$id0.png')
		import re
		res = re.search(r'id=(\d+)', self._link)
		if res:
			s = s.replace('$id', res.group(1))
			self._dict['thumbnail'] = s
			debug(self._dict['thumbnail'])

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'), settings=self.settings)
				
		return True


def write_movie(item, settings, path):
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
		STRMWriter(origin_url(item.link)).write(filename, path, parser=parser, settings=settings)
		NFOWriter(parser, movie_api=parser.movie_api()).write_movie(filename, path)
		if settings.bluebird_preload_torrents:
			from downloader import TorrentDownloader
			TorrentDownloader(item.link, settings.torrents_path(), settings).download()
	else:
		skipped(item)
		
	del parser
		
def write_movies(rss_url, path, settings):
	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(real_url(rss_url))

		cnt = 0
		settings.progress_dialog.update(0, 'bluebird', path)

		for item in d.entries:
			item.link = origin_url(item.link)
			write_movie(item, settings, path)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'bluebird', path)


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

	return	# TODO: Later

	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(real_url(rss_url))

		cnt = 0
		settings.progress_dialog.update(0, 'bluebird', path)

		for item in d.entries:
			item.link = origin_url(item.link)
			write_tvshow(item, settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'bluebird', path)


def get_rss_url(f_id, passkey):
	return origin_url('/rss.php?cat=' + str(f_id) + '&passkey=' + passkey)

def create_session(settings):
	if create_session.session:
		return create_session.session

	session = requests.session()

	if not settings.bluebird_login or not settings.bluebird_password:
		return None

	data = { 'username': settings.bluebird_login, 'password': settings.bluebird_password  }

	headers = {
		'Host': 'bluebird-hd.org',
		'Origin': real_url('/'),
		'Referer': real_url('/login.php'),
		'Content-Type': 'application/x-www-form-urlencoded'
	}

	r = session.post(real_url('/takelogin.php'), headers=headers, data=data)

	if r.ok and 'signup.php' not in r.text:
		create_session.session = session
		return session

	return None

create_session.session = None


def get_passkey(settings):

	s = create_session(settings)
	if not s:
		return None

	r = s.get(real_url('/my.php'))
	if r.ok:
		txt = r.text
		indx = txt.index(u'Мой пасскей')
		if indx >= 0:
			txt = txt[indx:]
			i1 = txt.index('<b>')
			i2 = txt.index('</b>')
			txt = txt[i1+3:i2]
			return txt

	return None

def run(settings):
	if not settings.bluebird_passkey:
		settings.bluebird_passkey = get_passkey(settings)
	if not settings.bluebird_passkey:
		return

	if settings.animation_save:
		write_movies(get_rss_url(2, settings.bluebird_passkey), settings.animation_path(), settings)

	if settings.documentary_save:
		write_movies(get_rss_url(3, settings.bluebird_passkey), settings.documentary_path(), settings)

	if settings.movies_save:
		write_movies(get_rss_url(1, settings.bluebird_passkey), settings.movies_path(), settings)

	if settings.tvshows_save:
		write_tvshows(get_rss_url(6, settings.bluebird_passkey), settings.tvshow_path(), settings)


def make_search_url(what, IDs, imdb, settings):
	url = u'/browse.php'
	url += '?c=' + str(IDs)
	#url += '&passkey=' + settings.bluebird_passkey
	if imdb is None:
		url += '&search=' + urllib2.quote(what.encode('cp1251'))
	url += '&dsearch=' + imdb
	return origin_url(url)

def get_cookies(settings):
	s = settings.bluebird_cookies
	ss = s.split('; ')
	ss = [ i.split('=') for i in ss ]
	return { i[0]:i[1] for i in ss }

def search_generate(what, imdb, settings, path_out):

	count = 0
	session = create_session(settings)

	if not session:
		return 0

	if settings.movies_save:
		url = make_search_url(what, 1, imdb, settings)
		result1 = search_results(imdb, session, settings, url, 1)
		count += make_search_strms(result1, settings, 'movie', settings.movies_path(), path_out)

	if settings.animation_save and count == 0:
		url = make_search_url(what, 2, imdb, settings)
		result2 = search_results(imdb, session, settings, url, 2)
		count += make_search_strms(result2, settings, 'movie', settings.animation_path(), path_out)

	if settings.documentary_save and count == 0:
		url = make_search_url(what, 3, imdb, settings)
		result3 = search_results(imdb, session, settings, url, 3)
		count += make_search_strms(result3, settings, 'movie', settings.documentary_path(), path_out)

	if settings.tvshows_save and count == 0:
		url = make_search_url(what, 6, imdb, settings)
		result4 = search_results(imdb, session, settings, url, 6)
		count += make_search_strms(result4, settings, 'tvshow', settings.tvshow_path(), path_out)

	return count


def make_search_strms(result, settings, type, path, path_out):
	count = 0
	for item in result:
		link = item['link']
		parser = item['parser']
		if link:
			settings.progress_dialog.update(count * 100 / len(result), 'bluebird', parser.get_value('full_title'))

			if type == 'movie':
				import movieapi
				_path = movieapi.write_movie(parser.get_value('full_title'), link, settings, parser, path, skip_nfo_exists=True, download_torrent=False)
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


class TrackerPostsEnumerator(object):
	_items = []

	def __init__(self, session, cookies=None):
		self._s = session
		self._items[:] = []
		self.cookies = cookies

	def items(self):
		return self._items

	def process_page(self, url):
		request = self._s.get(real_url(url), cookies=self.cookies)
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
	
	from log import dump_context
	with dump_context('bluebird.enumerator.process_page'):
		enumerator.process_page(url)

	result = []
	for post in enumerator.items():
		if 'seeds' in post and int(post['seeds']) < 5:
			continue

		if str(post.get('cat', '')) != str(cat):
			continue

		# full_title, content, link, settings

		url = real_url(post['a'])
		page = session.get(url, headers={'Referer': real_url('/browse.php')})

		soup = BeautifulSoup(page.text, "html.parser")

		content = ''
		tbl = soup.find('table', attrs={'id': 'highlighted'})

		for td in tbl.find_all('td', class_='heading'):
			tdn = td.next_sibling
			content += unicode(tdn)

		img = soup.find('img', attrs = {'title': "IMDB"})
		if img:
			content += unicode(img.parent)

		img = soup.find('img', attrs = {'title': u"Кинопоиск"})
		if img:
			content += unicode(img.parent)

		parser = DescriptionParser(post['title'], content, origin_url(post['a']), settings=settings, imdb=imdb)
		
		debug(u'%s %s %s' % (post['title'], str(parser.parsed()), parser.get_value('imdb_id')))
		if parser.parsed(): # and parser.get_value('imdb_id') == imdb:
			result.append({'parser': parser, 'link': origin_url(post['dl_link'])})

	return result


def download_torrent(url, path, settings):
	if not settings.bluebird_passkey:
		settings.bluebird_passkey = get_passkey(settings)
	if not settings.bluebird_passkey:
		return False

	from base import save_hashes
	save_hashes(path)
	url = url.replace('details.php', 'download.php')
	if not 'passkey' in url:
		url += '&passkey=' + settings.bluebird_passkey

	try:
		response = urllib2.urlopen(real_url(url))
		data = response.read()
		if not data.startswith('d8:'):
			return False
		with filesystem.fopen(path, 'wb') as f:
			f.write(data)
		save_hashes(path)
		return True
	except BaseException as e:
		print_tb(e)
		return False

def login(user, passw, code):
	pass