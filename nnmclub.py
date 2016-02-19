# -*- coding: utf-8 -*-
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

import tvshowapi


_RSS_URL = 'http://nnm-club.me/forum/rss-topic.xml'
_BASE_URL = 'http://nnm-club.me/forum/'
_HD_PORTAL_URL = _BASE_URL + 'portal.php?c=11'

MULTHD_URL = 'http://nnm-club.me/forum/viewforum.php?f=661'

_NEXT_PAGE_SUFFIX = '&start='


class DescriptionParser(DescriptionParserBase):
	def __init__(self, content, settings=None, tracker=False):
		Informer.__init__(self)

		self._dict.clear()
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
				self._link = _BASE_URL + a['href']
				print self._link
			except:
				# print a.__repr__()
				return False

			full_title = a.get_text().strip(' \t\n\r')
			print 'full_title: ' + full_title.encode('utf-8')

			self.parse_title(full_title)

			if self.need_skipped(full_title):
				return False

			fname = base.make_fullpath(self.make_filename(), '.strm')
			if base.STRMWriterBase.has_link(fname, self._link):
				print 'Already exists'
				return False

			r = requests.get(self._link)
			if r.status_code == requests.codes.ok:
				return self.parse_description(r.text)

		return False

	def parse_description(self, html_text):
		self.soup = BeautifulSoup(clean_html(html_text), 'html.parser')

		tag = u''
		self._dict['gold'] = False
		for a in self.soup.select('img[src="images/gold.gif"]'):
			self._dict['gold'] = True
			print 'gold'

		for span in self.soup.select('span.postbody span'):
			try:
				text = span.get_text()
				tag = self.get_tag(text)
				if tag != '':
					if tag != u'plot':
						self._dict[tag] = base.striphtml(unicode(span.next_sibling).strip())
					else:
						self._dict[tag] = base.striphtml(unicode(span.next_sibling.next_sibling).strip())
					print '%s (%s): %s' % (text.encode('utf-8'), tag.encode('utf-8'), self._dict[tag].encode('utf-8'))
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

		if count_id > 1:
			return False

		for img in self.soup.select('var.postImg'):  # ('img.postImg'):
			try:
				self._dict['thumbnail'] = img['title']
				print '!!!!!!!!!!!!!!thumbnail: ' + self._dict['thumbnail']
				break
			except:
				pass

		self.parse_country_studio()

		if self.settings:
			if self.settings.use_kinopoisk:
				for kp_id in self.soup.select('#kp_id'):
					self._dict['kp_id'] = kp_id['href']

		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'))

		return True

	def link(self):
		return self._link

class DescriptionParserTVShows(DescriptionParser):

	def need_skipped(self, full_title):
		for phrase in [u'[EN]', u'[EN / EN Sub]', u'[Фильмография]', u'[ISO]', u'DVD', u'стереопара', u'Half-SBS']:
			if phrase in full_title:
				print 'Skipped by: ' + phrase.encode('utf-8')
				return True
		return False


class DescriptionParserRSS(DescriptionParser):
	def __init__(self, title, description, settings=None):
		Informer.__init__(self)

		self._dict.clear()
		self.content = description
		self.settings = settings
		self._dict['full_title'] = title.strip(' \t\n\r')
		self.OK = self.parse()

	def parse(self):
		full_title = self._dict['full_title']
		print 'full_title: ' + full_title.encode('utf-8')

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
			self._link = a['href']
			print self._link
			break

		return result

class DescriptionParserRSSTVShows(DescriptionParserRSS, DescriptionParserTVShows):
	pass

class PostsEnumerator(object):
	# ==============================================================================================
	_items = []

	def __init__(self):
		self._s = requests.Session()

	def process_page(self, url):
		request = self._s.get(url)
		self.soup = BeautifulSoup(clean_html(request.text), 'html.parser')
		print url

		for tbl in self.soup.select('table.pline'):
			self._items.append(tbl)

	def items(self):
		return self._items

class TrackerPostsEnumerator(PostsEnumerator):
	def process_page(self, url):
		request = self._s.get(url)
		self.soup = BeautifulSoup(clean_html(request.text), 'html.parser')
		print url

		for a in  self.soup.find_all('a', class_ = 'topictitle'): #self.soup.select('a.topictitle'):
			td = a.find_parent('td')
			if td and not td.find('span', class_ = 'tDL'):
				continue
			self._items.append(a)

def write_movie_rss(fulltitle, description, link, settings):
	parser = DescriptionParserRSS(fulltitle, description, settings)
	if parser.parsed():
		import movieapi
		if link:
			save_download_link(parser, settings, link)
		movieapi.write_movie(fulltitle, link, settings, parser)
		save_download_link(parser, settings, link)


def write_movie(post, settings, tracker):
	print '!-------------------------------------------'
	parser = DescriptionParser(post, settings=settings, tracker=tracker)
	if parser.parsed():
		print '+-------------------------------------------'
		full_title = parser.get_value('full_title')
		filename = parser.make_filename()
		if filename:
			print 'full_title: ' + full_title.encode('utf-8')
			print 'filename: ' + filename.encode('utf-8')
			print '-------------------------------------------+'
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
			if link:
				save_download_link(parser, settings, 'http://nnm-club.me/forum/' + link + '&uk=' + settings.nnmclub_passkey)

			from downloader import TorrentDownloader
			TorrentDownloader(parser.link(), settings.addon_data_path, settings).download()

		# time.sleep(1)

	del parser


def write_movies(content, path, settings, tracker=False):

	original_dir = filesystem.getcwd()

	if not filesystem.exists(path):
		filesystem.makedirs(path)

	try:
		filesystem.chdir(path)
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
	finally:
		filesystem.chdir(original_dir)

def save_download_link(parser, settings, link):
	try:
		path_store = filesystem.join(settings.addon_data_path, 'nnmclub')
		if not filesystem.exists(path_store):
			filesystem.makedirs(path_store)
		source = parser.link()
		match = re.search(r'\.php.+?t=(\d+)', source)
		if match:
			with filesystem.fopen(filesystem.join(path_store, match.group(1)), 'w') as f:
				f.write(link)
	except:
		pass

def write_tvshow(fulltitle, description, link, settings):
	parser = DescriptionParserRSSTVShows(fulltitle, description, settings)
	if parser.parsed():
		tvshowapi.write_tvshow(fulltitle, link, settings, parser)
		save_download_link(parser, settings, link)

def write_tvshows(rss_url, path, settings):
	original_dir = filesystem.getcwd()

	if not filesystem.exists(path):
		filesystem.makedirs(path)

	try:
		filesystem.chdir(path)

		d = feedparser.parse(rss_url)
		for item in d.entries:
			try:
				print item.title.encode('utf-8')
			except:
				continue
			write_tvshow(
				fulltitle=item.title,
				description=item.description,
				link=item.link,
				settings=settings)
	finally:
		filesystem.chdir(original_dir)

def write_movies_rss(rss_url, path, settings):
	original_dir = filesystem.getcwd()

	if not filesystem.exists(path):
		filesystem.makedirs(path)

	try:
		filesystem.chdir(path)

		d = feedparser.parse(rss_url)
		for item in d.entries:
			try:
				print item.title.encode('utf-8')
			except:
				continue
			write_movie_rss(
				fulltitle=item.title,
				description=item.description,
				link=item.link,
				settings=settings)
	finally:
		filesystem.chdir(original_dir)

def get_rss_url(f_id, passkey):
	return 'http://nnm-club.me/forum/rss2.php?f=' + str(f_id) + '&h=168&t=1&uk=' + passkey

def run(settings):
	passkey = get_passkey(settings)
	settings.nnmclub_passkey = passkey

	if settings.movies_save:
		write_movies_rss(get_rss_url('227,954', passkey), settings.movies_path(), settings)

	if settings.animation_save:
		write_movies_rss(get_rss_url(661, passkey), settings.animation_path(), settings)

	if settings.animation_tvshows_save:
		write_tvshows(get_rss_url(232, passkey), settings.animation_tvshow_path(), settings)

	if settings.tvshows_save:
		write_tvshows(get_rss_url(768, passkey), settings.tvshow_path(), settings)


def get_magnet_link(url):
	r = requests.get(url)
	if r.status_code == requests.codes.ok:
		soup = BeautifulSoup(clean_html(r.text), 'html.parser')
		for a in soup.select('a[href*="magnet:"]'):
			print a['href']
			return a['href']
	return None


def create_session(settings):
	s = requests.Session()

	r = s.get("http://nnm-club.me/forum/login.php")

	soup = BeautifulSoup(clean_html(r.text), 'html.parser')

	for inp in soup.select('input[name="code"]'):
		code = inp['value']
	# print code

	data = {"username": settings.nnmclub_login, "password": settings.nnmclub_password,
			"autologin": "on", "code": code, "redirect": "", "login": ""}
	login = s.post("http://nnm-club.me/forum/login.php", data=data,
				   headers={'Referer': "http://nnm-club.me/forum/login.php"})
	print 'Login status: %d' % login.status_code

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
		path_store = filesystem.join(settings.addon_data_path, 'nnmclub', match.group(1))
		if filesystem.exists(path_store):
			print '[nnm-club] Direct link found'
			with filesystem.fopen(path_store, 'r') as f:
				return f.read()
	return None

def download_torrent(url, path, settings):
	import shutil
	url = urllib2.unquote(url)
	print 'download_torrent:' + url

	href = None
	link = find_direct_link(url, settings)
	if link is None:
		s = create_session(settings)
		page = s.get(url)
		# print page.text.encode('cp1251')

		soup = BeautifulSoup(clean_html(page.text), 'html.parser')
		a = soup.select('td.gensmall > span.genmed > b > a')
		if len(a) > 0:
			href = 'http://nnm-club.me/forum/' + a[0]['href']
		print s.headers
	else:
		href = link
		response = urllib2.urlopen(link)
		#CHUNK = 256 * 1024
		with filesystem.fopen(path, 'wb') as f:
			shutil.copyfileobj(response, f)
			return True

		#r = requests.head(link)
		#print r.headers
		#return False


	if href:
		if link:
			r = requests.get(link)
		else:
			r = s.get(href, headers={'Referer': url})
		print r.headers

		# 'Content-Type': 'application/x-bittorrent'
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
	settings = Settings('../../..', nnmclub_pages=20)
	run(settings)
