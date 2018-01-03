# -*- coding: utf-8 -*-

import log
from log import debug


import re
import urllib2

from bs4 import BeautifulSoup

import base
import feedparser
import requests

import filesystem
from base import DescriptionParserBase, clean_html, Informer
from nfowriter import NFOWriter
from settings import Settings
from strmwriter import STRMWriter

import movieapi
import tvshowapi


_RSS_URL = 'http://nnm-club.me/forum/rss-topic.xml'
_BASE_URL = 'http://nnm-club.me/forum/'
_HD_PORTAL_URL = _BASE_URL + 'portal.php?c=11'

MULTHD_URL = 'http://nnm-club.me/forum/viewforum.php?f=661'

_NEXT_PAGE_SUFFIX = '&start='

#_mirror = 'nnm-club.name'

def real_url(url, settings):

	protocol = 'http'
	if settings.nnmclub_use_ssl:
		protocol = 'https'

	import urlparse
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult(protocol, settings.nnmclub_domain, res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	debug(res)
	return res


def origin_url(url):
	import urlparse
	res = urlparse.urlparse(url)
	res = urlparse.ParseResult('http', 'nnm-club.me', res.path, res.params, res.query, res.fragment)
	res = urlparse.urlunparse(res)
	return res


class DescriptionParser(DescriptionParserBase):
	def __init__(self, content, settings=None, tracker=False):
		Informer.__init__(self)

		self._dict = dict()
		self.content = content
		self.tracker = tracker
		self.settings = settings
		self.OK = self.parse()

	def get_tag(self, x):
		return {
			# u'Название:': u'title',
			# u'Оригинальное название:': u'originaltitle',
			# u'Год выхода:': u'year',
			u'Жанр:': u'genre',
			u'Режиссер:': u'director',
			u'Актеры:': u'actor',
			u'Описание:': u'plot',
			u'Продолжительность:': u'runtime',
			u'Качество видео:': u'format',
			u'Производство:': u'country_studio',
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

			found = re.search('^(.+?) ' + sep, full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title

	def get_original_title(self, full_title):
		if not ' / ' in full_title:
			return self.get_title(full_title)

		try:
			found = re.search('^.+? / (.+?) \(', full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title

	def get_year(self, full_title):
		try:
			found = re.search('\(([0-9]+)\)', full_title).group(1)
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
		a = None
		if self.tracker:
			a = self.content
		else:
			for __a in self.content.select('.substr a.pgenmed'):
				a = __a
				break

		if a != None:
			try:
				self._link = origin_url(_BASE_URL + a['href'])
				debug(self._link)
			except:
				# debug(a.__repr__())
				return False

			full_title = a.get_text().strip(' \t\n\r')
			debug('full_title: ' + full_title.encode('utf-8'))

			self.parse_title(full_title)

			if self.need_skipped(full_title):
				return False

			fname = base.make_fullpath(self.make_filename(), '.strm')
			if base.STRMWriterBase.has_link(fname, self._link):
				debug('Already exists')
				return False

			r = self.settings.session.get(self._link)
			if r.status_code == requests.codes.ok:
				return self.parse_description(r.text)

		return False

	def parse_description(self, html_text):
		self.soup = BeautifulSoup(clean_html(html_text), 'html.parser')

		tag = u''
		self._dict['gold'] = False
		for a in self.soup.select('img[src="images/gold.gif"]'):
			self._dict['gold'] = True
			debug('gold')

		for span in self.soup.select('.postbody span'):
			try:
				text = span.get_text()
				tag = self.get_tag(text)
				if tag != '':
					if tag != u'plot':
						self._dict[tag] = base.striphtml(unicode(span.next_sibling).strip())
					else:
						self._dict[tag] = base.striphtml(unicode(span.next_sibling.next_sibling).strip())
					debug('%s (%s): %s' % (text.encode('utf-8'), tag.encode('utf-8'), self._dict[tag].encode('utf-8')))
			except:
				pass
		if 'genre' in self._dict:
			self._dict['genre'] = self._dict['genre'].replace('.', '')

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

		if count_id > 1:
			return False

		img = self.soup.find('var', class_='postImg')
		if  img:
			try:
				self._dict['thumbnail'] = img['title'].split('?link=')[-1]
				debug('!!!!!!!!!!!!!!thumbnail: ' + self._dict['thumbnail'])
			except:
				pass

		if 'thumbnail' not in self._dict:
			imgs = self.soup.select('span.postbody > img')
			try:
				self._dict['thumbnail'] = imgs[0]['src'].split('?link=')[-1]
				debug('!!!!!!!!!!!!!!thumbnail: ' + self._dict['thumbnail'])
			except BaseException as e:
				pass

		self.parse_country_studio()

		kp = self.soup.select_one('div.kpi a')
		if not kp:
			kp = self.soup.select_one('#kp_id')
		if kp:
			self._dict['kp_id'] = kp['href']

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'), self.settings)

		return True

	def link(self):
		return origin_url(self._link)

class DescriptionParserTVShows(DescriptionParser):

	def need_skipped(self, full_title):
		for phrase in [u'[EN]', u'[EN / EN Sub]', u'[Фильмография]', u'[ISO]', u'DVD', u'стереопара', u'Half-SBS']:
			if phrase in full_title:
				debug('Skipped by: ' + phrase.encode('utf-8'))
				return True
		return False


class DescriptionParserRSS(DescriptionParser):
	def __init__(self, title, description, settings=None):
		Informer.__init__(self)

		self._dict = dict()
		self.content = description
		self.settings = settings
		self._dict['full_title'] = title.strip(' \t\n\r')
		self.OK = self.parse()

	def parse(self):
		full_title = self._dict['full_title']
		debug('full_title: ' + full_title.encode('utf-8'))

		if self.need_skipped(full_title):
			return False

		self.parse_title_tvshow(full_title)

		html_doc = '''<?xml version="1.0" encoding="UTF-8" ?>
					<html>
						<span class="postbody">
					''' + \
				   self.content.encode('utf-8') + \
				   '''
						</span>
					</html>'''
		result = self.parse_description(html_doc)

		for a in self.soup.select('.postbody a'):
			self._link = origin_url(a['href'])
			debug(self._link)
			break

		return result

class DescriptionParserRSSTVShows(DescriptionParserRSS, DescriptionParserTVShows):
	pass

class PostsEnumerator(object):
	# ==============================================================================================
	_items = []

	def __init__(self, session):
		self._s = session

		self._items[:] = []
		self.settings = None

	def process_page(self, url):
		request = self._s.get(url)
		self.soup = BeautifulSoup(clean_html(request.text), 'html.parser')
		debug(url)

		for tbl in self.soup.select('table.pline'):
			self._items.append(tbl)

	def items(self):
		return self._items

class TrackerPostsEnumerator(PostsEnumerator):
	def __init__(self, session):
		self._s = session
		self._items[:] = []

	def process_page(self, url):
		request = self._s.get(url)
		self.soup = BeautifulSoup(clean_html(request.text), 'html.parser')
		debug(url)

		tbl = self.soup.find('table', class_='tablesorter')
		if tbl:
			tbody = tbl.find('tbody')
			if tbody:
				for tr in tbody.find_all('tr'):
					item = {}
					cat_a = tr.find('a', class_='gen')
					if cat_a:
						item['category'] = cat_a['href']
					topic_a = tr.find('a', class_='topictitle')
					if topic_a:
						item['a'] = topic_a
					dl_a = tr.find('a', attrs={'rel': "nofollow"})
					if dl_a:
						item['dl_link'] = dl_a['href']

					seeds_td = tr.find('td', attrs={'title': "Seeders"})
					if seeds_td:
						item['seeds'] = seeds_td.get_text()

					self._items.append(item.copy())


def write_movie_rss(fulltitle, description, link, settings):
	parser = DescriptionParserRSS(fulltitle, description, settings)
	if parser.parsed():
		#if link:
		#	save_download_link(parser, settings, link)
		movieapi.write_movie(fulltitle, link, settings, parser)
		#save_download_link(parser, settings, link)


def write_movie(post, settings, tracker):
	debug('!-------------------------------------------')
	parser = DescriptionParser(post, settings=settings, tracker=tracker)
	if parser.parsed():
		debug('+-------------------------------------------')
		full_title = parser.get_value('full_title')
		filename = parser.make_filename()
		if filename:
			debug('full_title: ' + full_title.encode('utf-8'))
			debug('filename: ' + filename.encode('utf-8'))
			debug('-------------------------------------------+')
			STRMWriter(parser.link()).write(filename,
											parser=parser,
											settings=settings)
			NFOWriter(parser, movie_api = parser.movie_api()).write_movie(filename)

			link = None
			try:
				link = post.select('a[href*="download.php"]')[0]['href']
			except:
				try:
					link = post.find_parent('tr').select('a[href*="download.php"]')[0]['href']
				except:
					pass
			#if link:
			#	save_download_link(parser, settings, 'http://nnm-club.me/forum/' + link + '&uk=' + settings.nnmclub_passkey)

			from downloader import TorrentDownloader
			TorrentDownloader(parser.link(), settings.torrents_path(), settings).download()

		# time.sleep(1)

	del parser


def write_movies(content, path, settings, tracker=False):

	with filesystem.save_make_chdir_context(path):
		# ---------------------------------------------
		if tracker:
			_ITEMS_ON_PAGE = 50
			enumerator = TrackerPostsEnumerator()
		else:
			_ITEMS_ON_PAGE = 15
			enumerator = PostsEnumerator()
		for i in range(settings.nnmclub_pages):
			enumerator.process_page(content + _NEXT_PAGE_SUFFIX + str(i * _ITEMS_ON_PAGE))

		for post in enumerator.items():
			write_movie(post, settings, tracker)
		# ---------------------------------------------


def save_download_link(parser, settings, link):
	#try:
	if True:
		path_store = filesystem.join(settings.torrents_path(), 'nnmclub')
		if not filesystem.exists(path_store):
			filesystem.makedirs(path_store)
		source = parser.link()
		match = re.search(r'\.php.+?t=(\d+)', source)
		if match:
			with filesystem.fopen(filesystem.join(path_store, match.group(1)), 'w') as f:
				f.write(link)
	#except:
	#	pass


def write_tvshow(fulltitle, description, link, settings):
	parser = DescriptionParserRSSTVShows(fulltitle, description, settings)
	if parser.parsed():
		#if link:
		#	save_download_link(parser, settings, link)
		tvshowapi.write_tvshow(fulltitle, link, settings, parser)
		#save_download_link(parser, settings, link)


def title(rss_url):
	if 'dl=' in rss_url:
		return 'nnm-club favorites'
	else:
		return 'nnm-club'


def write_tvshows(rss_url, path, settings):
	debug('------------------------- NNM Club: %s -------------------------' % rss_url)

	with filesystem.save_make_chdir_context(path):
		r = settings.session.get(rss_url)
		if not r.ok:
			return

		d = feedparser.parse(r.content)

		cnt = 0
		settings.progress_dialog.update(0, title(rss_url), path)

		for item in d.entries:
			try:
				debug(item.title.encode('utf-8'))
			except:
				continue
			write_tvshow(
				fulltitle=item.title,
				description=item.description,
				link=origin_url(item.link),
				settings=settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), title(rss_url), path)


def write_movies_rss(rss_url, path, settings):

	debug('------------------------- NNM Club: %s -------------------------' % rss_url)

	with filesystem.save_make_chdir_context(path):
		r = settings.session.get(rss_url)
		if not r.ok:
			return

		d = feedparser.parse(r.content)

		cnt = 0
		settings.progress_dialog.update(0, title(rss_url), path)

		for item in d.entries:
			try:
				debug(item.title.encode('utf-8'))
			except:
				continue
			write_movie_rss(
				fulltitle=item.title,
				description=item.description,
				link=origin_url(item.link),
				settings=settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), title(rss_url), path)


def get_uid(settings, session=None):
	if session is None:
		session = create_session(settings)
	try:
		page = session.get('http://nnm-club.me/')
		if page.status_code == requests.codes.ok:
			soup = BeautifulSoup(clean_html(page.text), 'html.parser')
			'''
			a = soup.select_one('a[href*="profile.php"]')
			if a is None:
				return None
			'''
			for a in soup.select('a.mainmenu'):
				m = re.search('profile.php.+?u=(\d+)', a['href'])
				if m:
					return m.group(1)
		else:
			debug('page.status_code: ' + str(page.status_code))
	except BaseException as e:
		log.print_tb(e)
		pass

	return None


def get_rss_url(f_id, passkey, settings):
	pkstr = '&uk=' + passkey + '&r' if passkey else ''
	return 'http://nnm-club.me/forum/rss2.php?f=' + str(f_id) + '&h=' + str(settings.nnmclub_hours) + '&t=1' + pkstr


def get_fav_rss_url(f_id, passkey, uid):
	pkstr = '&uk=' + passkey + '&r' if passkey else ''
	return 'http://nnm-club.me/forum/rss2.php?f=' + str(f_id) + '&dl=' + str(uid) + '&t=1'  + pkstr


def run(settings):
	session = create_session(settings)

	passkey = None
	"""
	passkey = get_passkey(settings, session)

	if passkey is None:
		return

	settings.nnmclub_passkey = passkey
	"""

	uid = get_uid(settings, session)

	if uid is not None:
		debug('NNM uid: ' + str(uid))

		write_movies_rss(get_fav_rss_url('227,954', passkey, uid), settings.movies_path(), settings)
		write_movies_rss(get_fav_rss_url(661, passkey, uid), settings.animation_path(), settings)
		write_tvshows(get_fav_rss_url(232, passkey, uid), settings.animation_tvshow_path(), settings)
		write_tvshows(get_fav_rss_url(768, passkey, uid), settings.tvshow_path(), settings)

	if settings.movies_save:
		write_movies_rss(get_rss_url('227,954', passkey, settings), settings.movies_path(), settings)

	if settings.animation_save:
		write_movies_rss(get_rss_url(661, passkey, settings), settings.animation_path(), settings)

	if settings.animation_tvshows_save:
		write_tvshows(get_rss_url(232, passkey, settings), settings.animation_tvshow_path(), settings)

	if settings.tvshows_save:
		write_tvshows(get_rss_url(768, passkey, settings), settings.tvshow_path(), settings)


def get_magnet_link(url):
	'''
	r = requests.get(real_url(url), verify=False)
	if r.status_code == requests.codes.ok:
		soup = BeautifulSoup(clean_html(r.text), 'html.parser')
		for a in soup.select('a[href*="magnet:"]'):
			debug(a['href'])
			return a['href']
	'''
	return None


def create_session(settings):
	try:
		return settings.session
	except AttributeError:
		s = requests.Session()

		cookies = None
		if settings.nnmclub_use_ssl:
			cookies = dict( ssl='enable_ssl' )

		r = s.get(real_url("http://nnm-club.me/forum/login.php", settings), verify=False)

		soup = BeautifulSoup(clean_html(r.text), 'html.parser')

		code = ''
		for inp in soup.select('input[name="code"]'):
			code = inp['value']
		# debug(code)

		data = {"username": settings.nnmclub_login, "password": settings.nnmclub_password,
				"autologin": "on", "code": code, "redirect": "", "login": ""}
		login = s.post(real_url("http://nnm-club.me/forum/login.php", settings), data=data, verify=False, cookies=cookies,
					   headers={'Referer': real_url("http://nnm-club.me/forum/login.php", settings)})
		debug('Login status: %d' % login.status_code)


		class MySession():
			def __init__(self, session, settings):
				self.session = session
				self.settings = settings
			def _prepare(self, kwargs):
				if settings.nnmclub_use_ssl:
					kwargs['verify'] = False
				kwargs['cookies'] = cookies
			def get(self, url, **kwargs):
				self._prepare(kwargs)
				return self.session.get(real_url(url, self.settings), **kwargs)
			def post(self, url, **kwargs):
				self._prepare(kwargs)
				return self.session.post(real_url(url, self.settings), **kwargs)

		s = MySession(s, settings)

		settings.session = s

		return s


def get_passkey(settings=None, session=None):
	if session is None and settings is None:
		return None

	if session is None:
		session = create_session(settings)

	page = session.get('http://nnm-club.me/forum/profile.php?mode=editprofile')

	soup = BeautifulSoup(clean_html(page.text), 'html.parser')

	next = False
	for span in soup.select('span.gen'):
		if next:
			return span.get_text()
		if span.get_text() == u'Текущий passkey:':
			next = True

	return None


def find_direct_link(url, settings):
	match = re.search(r'\.php.+?t=(\d+)', url)
	if match:
		path_store = filesystem.join(settings.torrents_path(), 'nnmclub', match.group(1))
		if filesystem.exists(path_store):
			debug('[nnm-club] Direct link found')
			with filesystem.fopen(path_store, 'r') as f:
				return f.read()
	return None


def download_torrent(url, path, settings):
	from base import save_hashes
	save_hashes(path)
	import shutil
	url = urllib2.unquote(url)
	debug('download_torrent:' + url)

	href = None
	link = None # find_direct_link(url, settings)
	if link is None:
		s = create_session(settings)
		page = s.get(url)
		# debug(page.text.encode('cp1251'))

		soup = BeautifulSoup(clean_html(page.text), 'html.parser')
		a = soup.select('td.gensmall > span.genmed > b > a')
		if len(a) > 0:
			href = 'http://nnm-club.me/forum/' + a[0]['href']
	else:
		href = linkd
		response = urllib2.urlopen(real_url(link, settings))
		#CHUNK = 256 * 1024
		with filesystem.fopen(path, 'wb') as f:
			shutil.copyfileobj(response, f)
		save_hashes(path)
		return True

		#r = requests.head(link)
		#debug(r.headers)
		#return False


	if href:
		def make_req():
			if link:
				return requests.get(real_url(link, settings), verify=False)
			else:
				return s.get(href, headers={'Referer': real_url(url, settings)})
			
		try:
			r = make_req()
			if not r.ok and r.status_code == 502:
				import time
				time.sleep(1)
				r = make_req()

			if 'Content-Type' in r.headers:
				if not 'torrent' in r.headers['Content-Type']:
					return False

			with filesystem.fopen(path, 'wb') as torr:
				for chunk in r.iter_content(100000):
					torr.write(chunk)
			save_hashes(path)
			return True
		except:
			pass

	return False


def make_search_url(what, IDs):
	url = u'http://nnm-club.me/forum/tracker.php'
	url += '?f=' + str(IDs)
	url += '&nm=' + urllib2.quote(what.encode('utf-8'))
	return url


def search_generate(what, imdb, settings, path_out):

	count = 0
	session = create_session(settings)

	if settings.movies_save:
		url = make_search_url(what, '227,954')
		result1 = search_results(imdb, session, settings, url)
		with filesystem.save_make_chdir_context(settings.movies_path()):
			count += make_search_strms(result1, settings, 'movie', path_out)

	if settings.animation_save and count == 0:
		url = make_search_url(what, '661')
		result2 = search_results(imdb, session, settings, url)
		with filesystem.save_make_chdir_context(settings.animation_path()):
			count += make_search_strms(result2, settings, 'movie', path_out)

	if settings.animation_tvshows_save and count == 0:
		url = make_search_url(what, '232')
		result3 = search_results(imdb, session, settings, url)
		with filesystem.save_make_chdir_context(settings.animation_tvshow_path()):
			count += make_search_strms(result3, settings, 'tvshow', path_out)

	if settings.tvshows_save and count == 0:
		url = make_search_url(what, '768')
		result4 = search_results(imdb, session, settings, url)
		with filesystem.save_make_chdir_context(settings.tvshow_path()):
			count += make_search_strms(result4, settings, 'tvshow', path_out)

	return count


def make_search_strms(result, settings, type, path_out):
	count = 0
	for item in result:
		link = item['link']
		parser = item['parser']

		settings.progress_dialog.update(count * 100 / len(result), 'NNM-Club', parser.get_value('full_title'))
		if link:
			if type == 'movie':
				path = movieapi.write_movie(parser.get_value('full_title'), link, settings, parser, skip_nfo_exists=True)
				path_out.append(path)
				count += 1
			if type == 'tvshow':
				path = tvshowapi.write_tvshow(parser.get_value('full_title'), link, settings, parser, skip_nfo_exists=True)
				path_out.append(path)
				count += 1

	return count


def search_results(imdb, session, settings, url):
	debug('search_results: url = ' + url)

	enumerator = TrackerPostsEnumerator(session)
	enumerator.settings = settings
	enumerator.process_page(real_url(url, settings))
	result = []
	for post in enumerator.items():
		if 'seeds' in post and int(post['seeds']) < 5:
			continue

		parser = DescriptionParser(post['a'], settings=settings, tracker=True)
		if parser.parsed() and parser.get_value('imdb_id') == imdb:
			result.append({'parser': parser, 'link': post['dl_link']})

	return result


if __name__ == '__main__':
	settings = Settings('../../..', nnmclub_pages=20)
	run(settings)
