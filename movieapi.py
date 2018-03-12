# -*- coding: utf-8 -*-

import log
from log import debug, print_tb


import json, re, base, filesystem

import urllib2, requests
from bs4 import BeautifulSoup

user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100'

def write_movie(fulltitle, link, settings, parser, path, skip_nfo_exists=False, download_torrent=True):
	debug('+-------------------------------------------')
	filename = parser.make_filename()
	if filename:
		debug('fulltitle: ' + fulltitle.encode('utf-8'))
		debug('filename: ' + filename.encode('utf-8'))
		debug('-------------------------------------------+')
		from strmwriter import STRMWriter
		STRMWriter(parser.link()).write(filename, path,
										parser=parser,
										settings=settings)
		from nfowriter import NFOWriter
		NFOWriter(parser, movie_api = parser.movie_api()).write_movie(filename, path, skip_nfo_exists=skip_nfo_exists)

		if download_torrent:
			from downloader import TorrentDownloader
			TorrentDownloader(parser.link(), settings.torrents_path(), settings).download()

		return filesystem.relpath( filesystem.join(path, base.make_fullpath(filename, '.strm')), start=settings.base_path())
	else:
		return None

def get_tmdb_api_key():
	try:
		import filesystem
		import xbmc
		home_path = xbmc.translatePath('special://home').decode('utf-8')
	except ImportError:
		cur = filesystem.dirname(__file__)
		home_path = filesystem.join(cur, '../..')

	key = 'ecbc86c92da237cb9faff6d3ddc4be6d'
	host = 'api.tmdb.org'
	try:
		xml_path = filesystem.join(home_path, 'addons/metadata.common.themoviedb.org/tmdb.xml')
		with filesystem.fopen(xml_path, 'r') as xml:
			content = xml.read()
			match = re.search(r'api_key=(\w+)', content)
			if match:
				key = match.group(1)
				debug('get_tmdb_api_key: ok')
			
			m = re.search(r'://(.+)/3/', content)
			if m:
				host = m.group(1)
	
	except BaseException as e:
		debug('get_tmdb_api_key: ' + str(e))

	return {'host': host, 'key': key }

def attr_text(s):
	return s.get_text()

def attr_split_slash(s):
	itms = s.get_text().split('/')
	return [i.strip() for i in itms]

def attr_year(s):
	import re
	m = re.search(r'(\d\d\d\d)', s.get_text())
	if m:
		return m.group(1)

def attr_genre(s):
	return [ a.get_text() for a in s.find_all('a') ]

class IDs(object):
	kp_by_imdb = {}
	imdb_by_kp = {}

	@staticmethod
	def id_by_kp_url(url):
		import re
		m = re.search(r"(\d\d+)", url)
		if m:
			return m.group(1)
		
		return None

	@staticmethod
	def get_by_kp(kp_url):
		return IDs.imdb_by_kp.get(IDs.id_by_kp_url(kp_url))

	@staticmethod
	def get_by_imdb(imdb_id):
		return IDs.kp_by_imdb.get(imdb_id)

	@staticmethod
	def set(imdb_id, kp_url):
		if imdb_id and kp_url:
			kp_id = IDs.id_by_kp_url(kp_url)
			IDs.imdb_by_kp[kp_id] = imdb_id
			IDs.kp_by_imdb[imdb_id] = kp_id

	@staticmethod
	def has_imdb(imdb_id):
		return imdb_id in IDs.kp_by_imdb

	@staticmethod
	def has_kp(kp_url):
		kp_id = IDs.id_by_kp_url(kp_url)
		return kp_id in IDs.imdb_by_kp

from soup_base import soup_base

class world_art_soup(soup_base):
	headers = {
		'Host': 						'www.world-art.ru',
		'Upgrade-Insecure-Requests': 	'1',
		'User-Agent':					user_agent,
		'X-Compress': 					'null',
	}

	def __init__(self, url):
		soup_base.__init__(self, url, self.headers)

class world_art_actors(world_art_soup):
	def __init__(self, url):
		world_art_soup.__init__(self, url)
		self._actors = []

	@property
	def actors(self):
		if not self._actors:
			def append_actor(tr):

				tds = tr.find_all('td', recursive=False)

				a = tds[1].find('a')
				act = {}
				if a:
					id = a['href'].split('?id=')[-1]
					id = id.split('&')[0]
					#if td.find('img', attrs={'src': "../img/photo.gif"}):
					#	act['photo'] = 'http://www.world-art.ru/img/people/10000/{}.jpg'.format(int(id))

					act['ru_name'] = tds[1].get_text()
					act['en_name'] = tds[2].get_text()
					act['role'] = tds[3].get_text()

					#act = { k:v for k, v in act.iteritems() if v }		## No python 2.6 compatible
					res = {}
					for k, v in act.iteritems():
						if v:
							res[k] = v

					self._actors.append(res)

			for b in self.soup.find_all('b'):
				if b.get_text() == u'Актёры':
					table = b.find_parent('table')
					table = table.find_next_siblings('table')[1]
					for tr_next in table.find_all('tr'):
						append_actor(tr_next)

					'''
					tr = b.find_parent('tr')
					if tr:
						for tr_next in tr.find_next_siblings('tr'):
							append_actor(tr_next)
					'''

		return self._actors

	def __getitem__(self, i):
		if isinstance(i, int):
			return self.actors[i]
		elif isinstance(i, str) or isinstance(i, unicode):
			for act in self.actors:
				if act['ru_name'] == i:
					return act
				if act['en_name'] == i:
					return act
		raise KeyError

class world_art_info(world_art_soup):
	Request_URL = "http://www.world-art.ru/%s"

	attrs = [
		(u'Названия', 'knowns', attr_split_slash),
		(u'Производство', 'country', attr_text),
		(u'Хронометраж', 'runtime', attr_text),
		(u'Жанр', 'genre', attr_genre),
		(u'Первый показ', 'year', attr_year),
		(u'Режиссёр', 'director', attr_text),
	]

	def __init__(self, url):
		world_art_soup.__init__(self, self.Request_URL % url)
		self._info_data = dict()
		self._actors = None

	@property
	def actors(self):
		if not self._actors:
			self._actors = world_art_actors(self.url.replace('cinema.php', 'cinema_full_cast.php'))
		return self._actors.actors

	@property
	def data(self):
		def next_td(td, fn):
			return fn(td.next_sibling.next_sibling)

		if not self._info_data:
			data = {}
			for td in self.soup.find_all('td', class_='review'):
				td_text = td.get_text()
				find = [item for item in self.attrs if td_text in item]
				if find:
					item = find[0]
					data[item[1]] = next_td(td, item[2])
			self._info_data = data.copy()

		return self._info_data

	def __getattr__(self, name):
		names = [i[1] for i in self.attrs]

		if name in names:
			return self.data[name]
		raise AttributeError

	@property
	def imdb(self):
		a = self.soup.select('a[href*=imdb.com]')
		for part in a[0]['href'].split('/'):
			if part.startswith('tt'):
				return part

	@property
	def kp_url(self):
		a = self.soup.select('a[href*=kinopoisk.ru]')
		return a[0]['href']

	@property
	def plot(self):
		p = self.soup.find('p', attrs ={'class':'review', 'align': 'justify'})
		if p:
			return p.get_text()

class world_art(world_art_soup):
	Request_URL = "http://www.world-art.ru/search.php?public_search=%s&global_sector=cinema"

	def __init__(self, title, year=None, imdbid=None, kp_url=None):
		import urllib
		url = self.Request_URL % urllib.quote_plus(title.encode('cp1251'))
		world_art_soup.__init__(self, url)

		self._title = title
		self._year = year
		self._imdbid = imdbid
		self._kp_url = kp_url

		self._info = None

	@property
	def info(self):
		if not self._info:
			results = self.search_by_title(self._title)

			#filter by year
			if self._year:
				results = [ item for item in results if item.year == self._year ]

			if self._imdbid:
				results = [ item for item in results if item.imdb == self._imdbid ]
				if results:
					self._info = results[0]
					return	self._info

			if self._kp_url:
				results = [ item for item in results if IDs.id_by_kp_url(item.kp_url) == IDs.id_by_kp_url(self._kp_url) ]
				if results:
					self._info = results[0]
					return	self._info

			# filter by title
			for item in results:
				if self._title in item.knowns:
					self._info = item
					return	self._info

			self._info = 'No info'

		#for info in results:
		#	imdb = info.imdb

		if self._info == 'No info':
			raise AttributeError

		return self._info

	def search_by_title(self, title):
		result = []
		
		for meta in self.soup.find_all('meta'):
			# 	meta	<meta content="0; url=/cinema/cinema.php?id=68477" http-equiv="Refresh"/>	Tag
			if meta.get('http-equiv') == "Refresh" and 'url=/cinema/cinema.php?id=' in meta.get('content'):
				url = meta.get('content').split('url=/')[-1]
				info = world_art_info(url)
				info.year		= self._year
				#info.knowns		= [ self._title ]

				result.append( info )

		for a in self.soup.find_all('a', class_="estimation"):

			info = world_art_info(a['href'])

			tr = a
			while tr.name != 'tr':
				tr = tr.parent
			info.year = tr.find('td').get_text()

			td = a.parent
			info.knowns = [ i.get_text() for i in td.find_all('i') ]

			result.append( info )
		return result

	def plot(self):
		return self.info.plot

	#def trailer(self):
	#	info = self.info
	def director(self):
		try:
			result = self.info.director
			result = result.replace(u'и другие', '')
			return [d.strip() for d in result.split(',')]
		except:
			return []

	def actors(self):
		try:
			return self.info.actors
		except:
			return []

class tmdb_movie_item(object):
	def __init__(self, json_data, type='movie'):
		self.json_data_ = json_data
		self.type = type

	def poster(self):
		try:
			return 'http://image.tmdb.org/t/p/w500' + self.json_data_['poster_path']
		except BaseException:
			return ''

	def fanart(self):
		try:
			return 'http://image.tmdb.org/t/p/original' + self.json_data_['backdrop_path']
		except BaseException:
			return ''

	def get_art(self):
		art = {}

		path = self.poster()

		art['thumb'] = path
		art['poster'] = path
		art['thumbnailImage'] = path

		art['fanart'] = self.fanart()

		return art

	def get_info(self):
		info = {}

		if 'genres' in self.json_data_:
			info['genre'] = u', '.join([i['name'] for i in self.json_data_['genres']])

		analogy = {
			'aired': 'release_date',
			'plot': 'overview',
			'title': 'name',
			'originaltitle': 'originalname',
		}

		for tag in analogy:
			if analogy[tag] in self.json_data_:
				info[tag] = self.json_data_[analogy[tag]]

		if 'aired' in info:
			aired = info['aired']
			m = re.search('(\d\d\d\d)', aired)
			if m:
				info['year'] = int(m.group(1))

		try:
			vid_item = self.json_data_['videos']['results'][0]
			if vid_item['site'] == 'YouTube':
				info['trailer'] = 'plugin://plugin.video.youtube/?action=play_video&videoid=' + vid_item['key']
		except BaseException:
			pass

		string_items = ['director', 'mpaa', 'title', 'originaltitle', 'duration', 'studio', 'code', 'album', 'votes', 'thumb']
		for item in string_items:
			if item in self.json_data_:
				info[item] = self.json_data_[item]

		#  'credits',

		return info

	def imdb(self):
		try:
			if 'imdb_id' in self.json_data_:
				return self.json_data_['imdb_id']
			elif 'external_ids' in self.json_data_ and 'imdb_id' in self.json_data_['external_ids']:
				return self.json_data_['external_ids']['imdb_id']

		except BaseException:
			return None


	def tmdb_id(self):
		if 'id' in self.json_data_:
			return self.json_data_['id']
		else:
			return None


class Object(object):
    pass

class KinopoiskAPI(object):
	# Common session for KP requests
	session = None

	kp_requests = []

	@staticmethod
	def make_url_by_id(kp_id):
		return 'http://www.kinopoisk.ru/film/' + str(kp_id) + '/'

	def __init__(self, kinopoisk_url = None, settings = None):
		from settings import Settings
		self.settings = settings if settings else Settings('')
		self.kinopoisk_url = kinopoisk_url
		self.soup = None
		self._actors = None

	def _http_get(self, url):
		for resp in KinopoiskAPI.kp_requests:
			if resp['url'] == url:
				return resp['response']

		r = requests.Response()

		if self.session is None:
			self.session = requests.session()


		try:
			if self.settings.kp_googlecache:
				r = self.get_google_cache(url)
			else:
				proxy = 'socks5h://socks.zaborona.help:1488'
				proxies = { 'http': proxy, 'https': proxy } if self.settings.kp_usezaborona else None
				headers = {'user-agent': user_agent}
				r = self.session.get(url, headers=headers, proxies=proxies, timeout=5.0)
		except requests.exceptions.ConnectionError as ce:
			r = requests.Response()
			r.status_code = requests.codes.service_unavailable

			debug(str(ce))
		except requests.exceptions.Timeout as te:
			r = requests.Response()
			r.status_code = requests.codes.request_timeout

			debug(str(te))

		if not self.settings.kp_googlecache:
			if 'captcha' in r.text:
				r = self.get_google_cache(url)

		KinopoiskAPI.kp_requests.append({'url': url, 'response': r})

		return r

	def get_google_cache(self, url):
		import urllib
		search_url = "http://www.google.com/search?q=" + urllib.quote_plus(url)
		headers = {'user-agent': user_agent}

		r = self.session.get(search_url, headers=headers, timeout=2.0)

		try:
			soup = BeautifulSoup(base.clean_html(r.text), 'html.parser')
			a = soup.find('a', class_='fl')
			if a:
				cache_url = a['href']

				import urlparse
				res = urlparse.urlparse(cache_url)
				res = urlparse.ParseResult(res.scheme if res.scheme else 'https', 
											res.netloc if res.netloc else 'webcache.googleusercontent.com', 
											res.path, res.params, res.query, res.fragment)
				cache_url = urlparse.urlunparse(res)

				#print cache_url
				r = self.session.get(cache_url, headers=headers, timeout=2.0)
			
				indx = r.text.find('<html')
				
				resp = Object()
				resp.status_code = r.status_code
				resp.text = r.text[indx:]

				return resp
		except BaseException as e:
			debug(str(e))
	
		return requests.Response()

	def makeSoup(self):
		if self.kinopoisk_url and self.soup is None:
			r = self._http_get(self.kinopoisk_url)
			if r.status_code == requests.codes.ok:
				text = base.clean_html(r.text)
				self.soup = BeautifulSoup(text, 'html.parser')

	def title(self):
		title = None

		self.makeSoup()
		if self.soup:
			h = self.soup.find('h1', class_ = 'moviename-big')
			if h:
				title = h.contents[0].strip()

		return title

	def originaltitle(self):
		title = None

		self.makeSoup()
		if self.soup:
			span = self.soup.find('span', attrs = {'itemprop': 'alternativeHeadline'})
			if span:
				title = span.get_text().strip('\t\r\n ')
		return title

	def year(self):
		self.makeSoup()
		if self.soup:
			for a in self.soup.find_all('a'):
				if '/lists/m_act%5Byear%5D/' in a.get('href', ''):
					return a.get_text()
		raise AttributeError

	def director(self):
		self.makeSoup()
		if self.soup:
			#<td itemprop="director"><a href="/name/535852/" data-popup-info="enabled">Роар Утхауг</a></td>
			td = self.soup.find('td', attrs={"itemprop": "director"})
			if td:
				return [ a.get_text() for a in td.find_all('a') if '/name' in a['href'] ]
		raise AttributeError

	def plot(self):
		plot = None

		self.makeSoup()
		if self.soup:
			div = self.soup.find('div', attrs={"itemprop": "description"})
			if div:
				plot = div.get_text().replace(u'\xa0', u' ')
				return plot

		raise AttributeError

	def base_actors_list(self):
		actors = []

		self.makeSoup()
		if self.soup:
			for li in self.soup.find_all('li', attrs={'itemprop': 'actors'}):
				a = li.find('a')
				if a:
					actors.append(a.get_text())

		if '...' in actors:
			actors.remove('...')
		if actors:
			return ', '.join(actors)
		else:
			return ''

	def actors(self):
		if self._actors is not None:
			return self._actors

		self._actors = []

		if self.kinopoisk_url:
			cast_url = self.kinopoisk_url + 'cast/'
			r = self._http_get(cast_url)
			if r.status_code == requests.codes.ok:
				text = base.clean_html(r.text)
				soup = BeautifulSoup(text, 'html.parser')
				
				if not soup:
					return []

				for actorInfo in soup.find_all('div', class_='actorInfo'):
					photo 		= actorInfo.select('div.photo a')[0]['href']
					#http://st.kp.yandex.net/images/actor_iphone/iphone360_30098.jpg
					#/name/7627/
					photo 		= photo.replace('/', '').replace('name', '')
					photo 		= 'http://st.kp.yandex.net/images/actor_iphone/iphone360_' + photo + '.jpg'
					ru_name		= actorInfo.select('div.info .name a')[0].get_text()
					en_name		= actorInfo.select('div.info .name span')[0].get_text()
					role		= actorInfo.select('div.info .role')[0].get_text().replace('... ', '')
					role 		= role.split(',')[0]
					self._actors.append({'photo': photo,'ru_name': ru_name,'en_name': en_name,'role': role})
		return self._actors

	def __trailer(self, element):
		for parent in element.parents:
			#debug(parent.tag)
			if parent.name == 'tr':
				for tr in parent.next_siblings:
					if not hasattr(tr, 'select'):
						continue
					if tr.name != 'tr':
						continue
					for a_cont in tr.select('a.continue'):
						if u'Высокое качество' in a_cont.get_text():
							trailer = a_cont['href']
							trailer = re.search('link=(.+?)$', trailer).group(1)
							try:
								debug('trailer: ' + trailer)
							except:
								pass
							return trailer
		return None

	def trailer(self):
		if self.kinopoisk_url:
			trailer_page = self.kinopoisk_url + 'video/type/1/'
			r = self._http_get(trailer_page)
			if r.status_code == requests.codes.ok:
				text = base.clean_html(r.text)
				soup = BeautifulSoup(text, 'html.parser')
				
				if not soup:
					return None

				for div in soup.select('tr td div div.flag2'):
					trailer = self.__trailer(div)
					if trailer:
						return trailer
				for a in soup.select('a.all'):
					return self.__trailer(a)
		return None

	def poster(self):
		raise AttributeError

class imdb_cast(soup_base):
	def __init__(self, url):
		soup_base(self, url + '/fullcredits')
		self._actors = []

	@property
	def actors(self):
		if not self._actors:
			tbl = self.soup.find('table', class_='cast_list')
			if tbl:
				for tr in tbl.find('tr'):
					if 'class' in tr:
						act = {}
						# https://images-na.ssl-images-amazon.com/images/M/MV5BMTkxMzk2MDkwOV5BMl5BanBnXkFtZTcwMDAxODQwMg@@._V1_UX32_CR0,0,32,44_AL_.jpg
						# https://images-na.ssl-images-amazon.com/images/M/MV5BMjExNzA4MDYxN15BMl5BanBnXkFtZTcwOTI1MDAxOQ@@._V1_SY1000_CR0,0,721,1000_AL_.jpg
						# https://images-na.ssl-images-amazon.com/images/M/MV5BMjExNzA4MDYxN15BMl5BanBnXkFtZTcwOTI1MDAxOQ@@._V1_UY317_CR7,0,214,317_AL_.jpg
						#img = tr.find('img')


class ImdbAPI(object):
	def __init__(self, imdb_id):
		headers = { 'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7' }

		resp = requests.get('http://www.imdb.com/title/' + imdb_id + '/', headers=headers)
		if resp.status_code == requests.codes.ok:
			text = base.clean_html(resp.content)
			self.page = BeautifulSoup(text, 'html.parser')

	def year(self):
		a = self.page.select_one('#titleYear > a')
		if a:
			return a.get_text()
		else:
			raise AttributeError

	def rating(self):
		span = self.page.find('span', attrs={'itemprop':'ratingValue'})
		if span:
			return span.get_text().replace(',', '.')
		else:
			raise AttributeError

	def runtime(self):
		t = self.page.find('time', attrs={'itemprop':'duration'})
		if t:
			return t['datetime'].replace('PT', '').replace('M', '')
		else:
			raise AttributeError

	def mpaa(self):
		rt = self.page.find('meta', attrs={'itemprop':'contentRating'})
		if rt:
			return 'Rated ' + rt['content']
		else:
			raise AttributeError

	def title(self):
		# <h1 itemprop="name" class="">
		h1 = self.page.find('h1', attrs={'itemprop':'name'})
		if h1:
			return unicode( h1.contents[0] ).replace(u'\xa0', u' ').strip()
		else:
			raise AttributeError

	def originaltitle(self):
		import re

		meta = self.page.find('meta', attrs={'property': 'og:title'})
		if meta:
			otitle = meta['content']
			otitle = re.sub(r'\(\d+\)', '', otitle)
			otitle = otitle.split('(TV')[0]
			return otitle.strip()

		raise AttributeError

	def type(self):
		# <div class="bp_heading">Episode Guide</div>
		for div in self.page.find_all('div', class_="bp_heading"):
			if div.get_text() == 'Episode Guide':
				return 'tvshow'

		return 'movie'


class KinopoiskAPI2(KinopoiskAPI):

	movie_cc = {}
	token = '037313259a17be837be3bd04a51bf678'

	def __init__(self, kinopoisk_url = None, settings = None):

		if kinopoisk_url:		
			self.kp_id = IDs.id_by_kp_url(kinopoisk_url)
			return super(KinopoiskAPI2, self).__init__(kinopoisk_url, settings)
		else:
			self.kp_id = None

	@property
	def data_cc(self):
		if self.kp_id is None:
			return {}

		if self.kp_id in self.movie_cc:
			return self.movie_cc[self.kp_id]

		url = 'http://getmovie.cc/api/kinopoisk.json?id=%s&token=%s' % (self.kp_id, self.token)
		r = requests.get(url)
		if r.status_code == requests.codes.ok:
			self.movie_cc[self.kp_id] = r.json()
			return self.movie_cc[self.kp_id]

		return {}

	def title(self):
		return self.data_cc.get('name_ru')

	def originaltitle(self):
		return self.data_cc.get('name_en')

	def year(self):
		return self.data_cc.get('year')

	def plot(self):
		return self.data_cc.get('description')		#.replace('<br/>', '<br/>')

	def actors(self):
		if self._actors is not None:
			return self._actors

		self._actors = []

		creators = self.data_cc.get('creators')
		if creators:
			for actor in creators.get('actor', []):
				self._actors.append({'photo': actor.get("photos_person"),
						'ru_name': actor.get("name_person_ru"),'en_name': actor.get("name_person_en")})

		return self._actors

	def trailer(self):
		return self.data_cc.get('trailer')

	def poster(self):
		return 'https://st.kp.yandex.net/images/film_big/{}.jpg'.format(self.kp_id)

class TMDB_API(object):
	api_url		= 'https://api.themoviedb.org/3'
	tmdb_api_key = get_tmdb_api_key()

	@staticmethod
	def url_imdb_id(idmb_id):
		
		url = 'http://%s/3/find/%s?api_key=%s&language=ru&external_source=imdb_id' % (TMDB_API.tmdb_api_key['host'], idmb_id, TMDB_API.tmdb_api_key['key'])
		tmdb_data 	= json.load(urllib2.urlopen( url ))

		for type in ['movie', 'tv']:
			try:
				id = tmdb_data['%s_results' % type][0]['id']
				return 'http://%s/3/' % TMDB_API.tmdb_api_key['host'] + type + '/' + str(id) + '?api_key=' + TMDB_API.tmdb_api_key['key'] + '&language=ru&append_to_response=credits'
			except: pass

		return None

	@staticmethod
	def search(title):
		url = 'http://%s/3/search/movie?query=' % TMDB_API.tmdb_api_key['host'] + urllib2.quote(title.encode('utf-8')) + '&api_key=' + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		movies = TMDB_API.tmdb_query(url)
		url = 'http://%s/3/search/tv?query=' % TMDB_API.tmdb_api_key['host'] + urllib2.quote(title.encode('utf-8')) + '&api_key=' + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		tv = TMDB_API.tmdb_query(url, 'tv')
		return movies + tv

	@staticmethod
	def tmdb_query(url, type='movie'):

		class tmdb_query_result(object):
			def __init__(self):
				self.result = []
				self.total_pages = None

			def append(self, item):
				self.result.append(item)

			def __iter__(self):
				for x in self.result:
					yield x

			def __add__(self, other):
				r = tmdb_query_result()
				r.result = self.result + other.result
				return r

			def __len__(self):
				return len(self.result)

			def __getitem__(self, index):
				return self.result[index]

		result = tmdb_query_result()
		try:
			data = json.load(urllib2.urlopen(url))
		except urllib2.HTTPError:
			return tmdb_query_result()

		if "total_pages" in data:
			result.total_pages = data["total_pages"]

		for tag in ['results', 'movie_results', 'tv_results']:
			if tag in data:
				for r in data[tag]:
					if not r['overview']:
						continue

					if '_results' in tag:
						type = tag.replace('_results', '')

					url2 = 'http://%s/3/' % TMDB_API.tmdb_api_key['host'] + type + '/' + str(
						r['id']) + '?api_key=' + TMDB_API.tmdb_api_key['key'] + '&language=ru&append_to_response=credits,videos,external_ids'
					data2 = json.load(urllib2.urlopen(url2))

					if 'imdb_id' in data2:
						result.append(tmdb_movie_item(data2, type))
					elif 'external_ids' in data2 and 'imdb_id' in data2['external_ids']:
						result.append(tmdb_movie_item(data2, type))

		return result

	@staticmethod
	def tmdb_by_imdb(imdb, type):
		url = 'http://%s/3/find/' % TMDB_API.tmdb_api_key['host'] + imdb + '?external_source=imdb_id&api_key=' + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		url += '&append_to_response=credits,videos,external_ids'
		debug(url)
		return TMDB_API.tmdb_query(url, type)

	@staticmethod
	def popular(page=1):
		url = 'http://%s/3/movie/popular?api_key=' % TMDB_API.tmdb_api_key['host'] + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		url += '&page={}'.format(page)
		return TMDB_API.tmdb_query(url)

	@staticmethod
	def popular_tv(page=1):
		url = 'http://%s/3/tv/popular?api_key=' % TMDB_API.tmdb_api_key['host'] + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		url += '&page={}'.format(page)
		return TMDB_API.tmdb_query(url, 'tv')

	@staticmethod
	def top_rated(page=1):
		url = 'http://%s/3/movie/top_rated?api_key=' % TMDB_API.tmdb_api_key['host'] + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		url += '&page={}'.format(page)
		return TMDB_API.tmdb_query(url)

	@staticmethod
	def top_rated_tv(page=1):
		url = 'http://%s/3/tv/top_rated?api_key=' % TMDB_API.tmdb_api_key['host'] + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		url += '&page={}'.format(page)
		return TMDB_API.tmdb_query(url, 'tv')

	@staticmethod
	def show_similar_t(page, tmdb_id, type):
		url = 'http://%s/3/' % TMDB_API.tmdb_api_key['host'] + type + '/' + str(
				tmdb_id) + '/similar?api_key=' + TMDB_API.tmdb_api_key['key'] + '&language=ru'
		url += '&page={}'.format(page)
		log.debug(url)
		return TMDB_API.tmdb_query(url, type)

	@staticmethod
	def show_similar(tmdb_id):
		return TMDB_API.show_similar_t(1, tmdb_id, 'movie') + TMDB_API.show_similar_t(1, tmdb_id, 'tv')

	@staticmethod
	def imdb_by_tmdb_search(orig, year):
		try:
			for res in TMDB_API.search(orig):
				r = res.json_data_

				release_date = r.get('release_date')
				if year and release_date and year not in release_date:
					continue

				r_title				= r.get('title')
				r_original_title	= r.get('original_title')

				if orig and ( orig == r_title or orig == r_original_title):
					return r['imdb_id']

		except BaseException as e:
			from log import print_tb
			print_tb(e)

		return None

	def __init__(self, imdb_id = None):
		if imdb_id:
			url_ = TMDB_API.url_imdb_id(imdb_id)
			try:
				if url_:
					self.tmdb_data 	= json.load(urllib2.urlopen( url_ ))
					debug('tmdb_data (' + url_ + ') \t\t\t[Ok]')
			except:
				pass

	def year(self):
		try:
			return self.tmdb_data['release_date'].split('-')[0]
		except:
			raise AttributeError

	def poster(self):
		return u'http://image.tmdb.org/t/p/original' + self.tmdb_data[u'poster_path']

	def fanart(self):
		return u'http://image.tmdb.org/t/p/original' + self.tmdb_data[u'backdrop_path']

	def set(self):
		try:
			if u'belongs_to_collection' in self.tmdb_data:
				belongs_to_collection = self.tmdb_data[u'belongs_to_collection']
				if belongs_to_collection and u'name' in belongs_to_collection:
					return belongs_to_collection[u'name']
		except:
			pass
			
		raise AttributeError

	def runtime(self):
		return self.tmdb_data['runtime']

	def tag(self):
		return self.tmdb_data[u'tagline']

	def plot(self):
		return self.tmdb_data['overview']

	def actors(self):
		try:
			cast = self.tmdb_data['credits']['cast']
		except AttributeError:
			return []

		result = []
		for actor in cast:
			res = {}
			res['en_name'] = actor['name']
			if actor.get('profile_path'):
				res['photo'] = 'http://image.tmdb.org/t/p/original' + actor['profile_path']
			if actor.get('character'):
				res['role'] = actor['character']
			if actor.get('order'):
				res['order'] = actor['order']

			result.append(res)
		return result

	def genres(self):
		ll = [g['name'] for g in self.tmdb_data['genres']]
		return ll

	def countries(self):
		from countries import ru
		cc = [c['iso_3166_1'] for c in self.tmdb_data['production_countries']]
		return [ru(c) for c in cc]
	
	def studios(self):
		ss = [ s['name'] for s in self.tmdb_data['production_companies']]
		return ss

class MovieAPI(object):

	APIs	= {}

	@staticmethod
	def get_by(imdb_id = None, kinopoisk_url = None, orig=None, year=None, imdbRaiting=None, settings = None):

		if not imdb_id:
			imdb_id = IDs.get_by_kp(kinopoisk_url) if kinopoisk_url else None
		if not imdb_id:
			try:
				_orig = orig
				_year = year

				if kinopoisk_url:
					kp = KinopoiskAPI(kinopoisk_url, settings)
					orig = kp.originaltitle()
					if not orig:
						orig = kp.title()
					year = kp.year()
					imdb_id = TMDB_API.imdb_by_tmdb_search(orig if orig else _orig, year if year else _year)

			except BaseException as e:
				from log import print_tb
				print_tb(e)

		if imdb_id and kinopoisk_url:
			IDs.set( imdb_id, kinopoisk_url)

		if imdb_id and imdb_id in MovieAPI.APIs:
			return MovieAPI.APIs[imdb_id], imdb_id
		elif kinopoisk_url and kinopoisk_url in MovieAPI.APIs:
			return MovieAPI.APIs[kinopoisk_url], imdb_id

		api = MovieAPI(imdb_id, kinopoisk_url, settings, orig, year)
		if imdb_id:
			MovieAPI.APIs[imdb_id] = api
		elif kinopoisk_url:
			MovieAPI.APIs[kinopoisk_url] = api

		return api, imdb_id

	def __init__(self, imdb_id = None, kinopoisk = None, settings = None, orig = None, year=None):

		self.providers = []

		self.tmdbapi = None
		self.imdbapi = None 
		self.kinopoiskapi = None
		self.worldartapi = None

		self._actors = None

		if imdb_id:
			self.tmdbapi = TMDB_API(imdb_id)
			self.imdbapi = ImdbAPI(imdb_id)

			self.providers = [self.tmdbapi, self.imdbapi]

		if kinopoisk:
			if not settings or settings.use_kinopoisk:
				self.kinopoiskapi = KinopoiskAPI(kinopoisk, settings)
				self.providers.append(self.kinopoiskapi)

		if imdb_id or kinopoisk:
			if not settings or settings.use_worldart:
				if not orig:
					orig = self.originaltitle()
				try:
					self.worldartapi = world_art(orig, imdbid=imdb_id, kp_url=kinopoisk)
					self.providers.append(self.worldartapi)
				except: 
					pass
			
	def actors(self):
		if self._actors is not None:
			return self._actors

		actors = []
		for api in [ self.kinopoiskapi, self.tmdbapi, self.worldartapi ]:
			if api:
				a = api.actors()
				if a:
					actors.append(a)

		if len(actors) > 0:
			self._actors = [ actor.copy() for actor in actors[0] ]
		else:
			self._actors = []

		for act in self._actors:
			for variant in actors[1:]:
				for add in variant:
					try:
						if act['en_name'] == add['en_name']:
							act.update(add)
					except KeyError:
						pass
				
		return self._actors

	def __getitem__(self, key):
		res = self.__getattr__(key)
		if callable(res):
			return res()
		else:
			raise AttributeError

	def get(self, key, default=None):
		try:
			return self.__getitem__(key)
		except AttributeError:
			return default
		
	def __getattr__(self, name):

		if name.startswith('_') or name in self.__dict__:
			return object.__getattribute__(self, name)

		for api in self.providers:
			try:
				res = api.__getattribute__(name)
				if res:
					return res
			except AttributeError:
				continue
		
		raise AttributeError

	def ru(self, name):
		def ru_text(text):
			r = 0
			nr = 0
			for ch in text:
				if ch >= u'А' and ch <= u'Я':
					r += 1
				elif ch >= u'а' and ch <= u'я':
					r += 1
				else:
					nr += 1
			return r > nr

		def ru_list(ll):
			for l in ll:
				if ru_text(l):
					return True
			return False

		for api in self.providers:
			try:
				res = api.__getattribute__(name)
				if res and callable(res):
					value = res()
					if isinstance(value, list):
						if ru_list(value):
							return value
					else:
						if ru_text(value):
							return value

			except AttributeError:
				continue
		
		raise AttributeError
		

if __name__ == '__main__':
	#for res in MovieAPI.search(u'Обитаемый остров'):
	#	print res.get_info()

	#for res in MovieAPI.popular_tv():
	#	print res.get_info()

	#MovieAPI.tmdb_query(
	#	'http://api.themoviedb.org/3/movie/tt4589186?api_key=f7f51775877e0bb6703520952b3c7840&language=ru')

	#api = MovieAPI(kinopoisk = 'https://www.kinopoisk.ru/film/894027/')
	#api = MovieAPI(kinopoisk = 'https://www.kinopoisk.ru/film/257774/')
	#api = world_art(title=u"Команда Тора")

	from settings import Settings
	settings = Settings('.')
	settings.kp_usezaborona = True
	api = KinopoiskAPI('https://www.kinopoisk.ru/film/257774/', settings)
	title = api.title()
	
	api = world_art(u'The Fate of the Furious', year='2017', kp_url='https://www.kinopoisk.ru/film/894027/')
	info = api.info
	knowns = info.knowns
	plot = info.plot

	actors = [act for act in info.actors]

	pass
