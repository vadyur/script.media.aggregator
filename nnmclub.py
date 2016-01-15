# -*- coding: utf-8 -*-

import os, re
from settings import Settings
from base import *
from nfowriter import *
from strmwriter import *
import requests, time, countries
from bencode import bdecode, BTFailure
import feedparser

_RSS_URL = 'http://nnm-club.me/forum/rss-topic.xml'
_BASE_URL = 'http://nnm-club.me/forum/'
_HD_PORTAL_URL = _BASE_URL + 'portal.php?c=11'

MULTHD_URL = 'http://nnm-club.me/forum/viewforum.php?f=661'

_NEXT_PAGE_SUFFIX='&start='

class DescriptionParser(DescriptionParserBase):
	
	def __init__(self, content, settings = None, tracker = False):
		Informer.__init__(self)
		
		self._dict.clear()
		self.content = content
		self.tracker = tracker
		self.settings = settings
		self.OK = self.parse()
		
	def get_tag(self, x):
		return {
			#u'Название:': u'title',
			#u'Оригинальное название:': u'originaltitle',
			#u'Год выхода:': u'year',
			u'Жанр:': u'genre',
			u'Режиссер:': u'director',
			u'Актеры:': u'actor',
			u'Описание:': u'plot',
			u'Продолжительность:': u'runtime',
			u'Качество видео:': u'format',
			u'Производство:' : u'country_studio',
			u'Видео:': u'video',
		}.get(x.strip(), u'')
		
	def clean(self, title):
		return title.strip(' \t\n\r')
		
	def get_title(self, full_title):
		try:
			sep = '/'
			if not ' / ' in full_title:
				sep = '\('
				
			found = re.search('^(.+?) ' + sep, full_title).group(1)
			return self.clean( found)
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
				self.__link = _BASE_URL + a['href']
				print self.__link
			except:
				#print a.__repr__()
				return False

			full_title = a.get_text().strip(' \t\n\r')
			print 'full_title: ' + full_title.encode('utf-8')
						
			self.parse_title(full_title)
			
			if self.need_skipped(full_title):
				return False
			
			fname = make_fullpath(self.make_filename(), '.strm')
			if STRMWriterBase.has_link(fname, self.__link):
				print 'Already exists'
				return False
			
			r = requests.get(self.__link)
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
						self._dict[tag] = base.striphtml( unicode(span.next_sibling).strip() )
					else:
						self._dict[tag] = base.striphtml( unicode(span.next_sibling.next_sibling).strip() )
					print '%s (%s): %s' % (text.encode('utf-8'), tag.encode('utf-8'), self._dict[tag].encode('utf-8'))
			except: pass
		if 'genre' in self._dict:
			self._dict['genre'] = self._dict['genre'].lower().replace('.','')

		count_id = 0
		for a in self.soup.select('#imdb_id'):
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

		for img in self.soup.select('var.postImg'): 		#('img.postImg'):
			try:
				self._dict['thumbnail'] = img['title']
				print '!!!!!!!!!!!!!!thumbnail: ' + self._dict['thumbnail']
				break
			except:
				pass
		
		if 'country_studio' in self._dict:
			parse_string = self._dict['country_studio']
			items = re.split(r'[/,|\(\);\\]', parse_string.replace(' - ', '/'))
			cntry = []
			stdio = []
			for s in items:
				s = s.strip()
				if len(s) == 0:
					continue
				cntry.append(s) if countries.isCountry(s) else stdio.append(s)
			self._dict['country'] = ', '.join(cntry)
			self._dict['studio'] = ', '.join(stdio)
			'''
			parts = parse_string.split(' / ')
			self._dict['country'] = parts[0]
			if len(parts) > 1:
				self._dict['studio'] = parts[1]
			'''

		if self.settings:
			if self.settings.use_kinopoisk:
				for kp_id in self.soup.select('#kp_id'):
					self._dict['kp_id'] = kp_id['href']
					
		self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'))
		
		return True
		
	def link(self):
		return self.__link

class DescriptionParserRSS(DescriptionParser):
	def __init__(self, title, description, settings = None):
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
			
		html_doc = '<?xml version="1.0" encoding="UTF-8" ?>\n<html>' + self.content.encode('utf-8') + '\n</html>'
		result = self.parse_description(html_doc)
		
		for a in self.soup.select('div.article_content a:nth-of-type(1)'):
			self.__link = _BASE_URL + a['href']
			print self.__link
			break
		
		return result
		

class PostsEnumerator(object):		
	#==============================================================================================
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
		
		for a in self.soup.select('a.topictitle'):
			self._items.append(a)
		
def write_movie(post, settings, tracker):
	print '!-------------------------------------------'
	parser = DescriptionParser(post, settings = settings, tracker = tracker)
	if parser.parsed():
		print '+-------------------------------------------'
		full_title = parser.get_value('full_title')
		filename = parser.make_filename()
		if filename:
			print 'full_title: ' + full_title.encode('utf-8')
			print 'filename: ' + filename.encode('utf-8')
			print '-------------------------------------------+'
			STRMWriter(parser.link()).write(filename, 
											rank = get_rank(full_title, parser, settings), 
											settings = settings)
			NFOWriter().write(parser, filename)
			
			#time.sleep(1)

	del parser

def write_movies(content, path, settings, tracker = False):
	
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

def write_tvshow(fulltitle, description, link, settings):
	parser = DescriptionParserRSS(fulltitle, description, settings)
	
	r = requests.get(link)
	if r.status_code == requests.codes.ok:
		data = r.content
		try:
			decoded = bdecode(data)
		except BTFailure:
			print "Can't decode torrent data (invalid torrent link? %s)" % link
			return
			
		files = []
		info = decoded['info']
		if 'files' in info:
			for i, f in enumerate(info['files']):
				#print i
				#print f
				fname = f['path'][-1]
				if TorrentPlayer.is_playable(fname):
					s = re.search('s(\d+)e(\d+)[\._ ]', fname, re.I)
					if s:
						season = int(s.group(1))
						episode = int(s.group(2))
						print 'Filename: %s\t index: %d\t season: %d\t episode: %d' % (fname, i, season, episode)
						files.append({ 'index': i, 'name': fname, 'season': season, 'episode': episode })
						
		if len(files) == 0:
			return
			
		files.sort(key=lambda x: (x['season'], x['episode']))

		title = parser.get_value('title')
		print title.encode('utf-8')
		originaltitle = parser.get_value('originaltitle')
		print originaltitle.encode('utf-8')

		tvshow_path = make_fullpath(title, '')
		print tvshow_path.encode('utf-8')
		
		try:
			save_path = filesystem.save_make_chdir(tvshow_path)
			
			imdb_id = parser.get('imdb_id', None)
			
			tvshow_api = TVShowAPI(originaltitle, title, imdb_id )
			NFOWriter().write(parser, 'tvshow', 'tvshow', tvshow_api)

			prevSeason = None
			episodes = None
			for f in files:
				try:
					new_season = prevSeason != f['season']
					if new_season:
						episodes = tvshow_api.episodes(f['season'])
					
					results = filter(lambda x: x['episodeNumber'] == f['episode'], episodes)
					episode = results[0] if len(results) > 0 else None
					if not episode:
						episode = {
							'title': title,
							'seasonNumber': f['season'],
							'episodeNumber': f['episode'],
							'image': '',
							'airDate': ''
							}
						
					season_path = 'Season %d' % f['season']
					tvshow_full_path = filesystem.save_make_chdir(season_path)
					
					filename = str(f['episode']) + '. ' + 'episode_s%de%d' % (f['season'], f['episode'])
					print filename.encode('utf-8')
					
					STRMWriter(link).write(filename, 
											episodeNumber = f['episode'], 
											seasonNumber = f['season'], 
											settings = settings, 
											rank = get_rank(fulltitle, parser, settings))
					NFOWriter().write_episode(episode, filename, tvshow_api)
					
					prevSeason = f['season']
					
				finally:
					filesystem.chdir(tvshow_full_path)
		finally:
			filesystem.chdir(save_path)
		
def write_tvshows(content, path, settings):
	original_dir = filesystem.getcwd()
	
	if not filesystem.exists(path):
		filesystem.makedirs(path)

	try:
		filesystem.chdir(path)
		
		d = feedparser.parse(content)
		for item in d.entries:
			try:
				print item.title.encode('utf-8')
			except:
				continue
			write_tvshow(							\
				fulltitle = item.title,				\
				description = item.description,		\
				link = item.link,					\
				settings = settings)
	finally:
		filesystem.chdir(original_dir)


def run(settings):
	write_movies(_HD_PORTAL_URL, settings.movies_path(), settings)
	write_movies(MULTHD_URL, settings.animation_path(), settings, tracker = True)
	#write_movies(_BASE_URL + 'portal.php?c=13', filesystem.join(settings.base_path(), u'Наши'), settings)
	
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
		#print code
	
	data = {"username": settings.nnmclub_login, "password": settings.nnmclub_password, 
																"autologin": "on", "code": code, "redirect": "", "login": "" }
	login = s.post("http://nnm-club.me/forum/login.php", data = data, headers={'Referer': "http://nnm-club.me/forum/login.php"})
	print 'Login status: %d' % login.status_code
	
	return s
	
def get_passkey(settings = None, session = None):
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
	
def download_torrent(url, path, settings):
	url = urllib2.unquote(url)
	print 'download_torrent:' + url
	s = create_session(settings)
	
	#print login.text.encode('cp1251')
	
	page = s.get(url)
	#print page.text.encode('cp1251')
	
	soup = BeautifulSoup(clean_html(page.text), 'html.parser')
	a = soup.select('td.gensmall > span.genmed > b > a')
	if len(a) > 0:
		href = 'http://nnm-club.me/forum/' + a[0]['href']
		print s.headers
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
	settings = Settings('../../..', nnmclub_pages = 20)
	run(settings)
	
