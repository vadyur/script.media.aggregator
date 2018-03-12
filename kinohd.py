# -*- coding: utf-8 -*-

from base import DescriptionParserBase, Informer
from soup_base import soup_base
from log import debug

protocol = 'http'
domain = 'kinohd.net'

class DescriptionParser(DescriptionParserBase, soup_base):
	def __init__(self, url, fulltitle, settings=None):
		Informer.__init__(self)
		soup_base.__init__(self, url)

		self._dict = dict()
		self._dict['link'] = url
		self._dict['full_title'] = fulltitle
		
		self.settings = settings
		self.OK = self.parse()

	def link(self):
		return self._dict['link']

	def parse(self):
		import re
		imdb = self.soup.find('img', class_="imdb_informer")
		if imdb:
			self._dict['imdb_id'] = re.search('(tt\d+)', imdb['src']).group(1)
		kp_a = self.soup.select('a[href*="/class/goo.php?url=http://www.kinopoisk.ru/film/"]')
		if kp_a:
			self._dict['kp_id'] = kp_a[0]['href'].split('url=')[-1]

		from bs4 import NavigableString
		tag = None
		for div in self.soup.find_all('div', class_="quotef"):
			txt = div.get_text()
			if u'Технические данные:' in txt:
				txt = ''
				for part in div.children:
					if isinstance(part, NavigableString):
						txt += unicode(part)
					else:
						if part.name == 'br':
							txt += '\n'
						else:
							txt += part.get_text()
						
				def write_tag(tag, value):
					self._dict[tag] = value.split(':')[-1].lstrip()

				for line in txt.split('\n'):
					if line.startswith(u'Видео:'):
						write_tag('video', line)
					if line.startswith(u'Перевод:'):
						write_tag('translate', line)

		if self.get_value('imdb_id'):
			self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'), settings=self.settings)
			return True


class BaseEnumerator:
	def __init__(self, content):
		from bs4 import BeautifulSoup
		self.soup = BeautifulSoup(content, "html.parser")

	def items(self):
		div = self.soup.find('div', class_="s5roundwrap")
		sz = self.size()
		root = div if sz == 30 else self.soup

		if root:
			count = 0
			for a in root.find_all('a'):
				href = a.get('href', '')
				if href.startswith('http://') and href.endswith(u'.html'):
					count += 1
					if count > sz:
						return

					box = a.parent.parent.parent
					fulltitle = box.find('h4').get_text() if box else u''
					yield a['href'], fulltitle

	def size(self):
		span = self.soup.find('span', class_="sresult")
		if span:
			import re
			m = re.search(r'(\d+)', span.get_text())
			if m:
				return int(m.group(1))

		return 30


class PostEnumerator(soup_base, BaseEnumerator):
	def __init__(self, url):
		soup_base.__init__(self, url)



def url(type):
	return '{}://{}/{}/'.format(protocol, domain, type)


class Process(object):
	def __init__(self, settings):
		self.settings = settings

	def process_movie(self, url, parser):
		import movieapi
		import filesystem

		api = parser.movie_api()
		genre = api['genres']
		if u'мультфильм' in genre:
			if not self.settings.animation_save:
				return
			base_path = self.settings.animation_path()
		elif u'документальный' in genre:
			if not self.settings.documentary_save:
				return
			base_path = self.settings.documentary_path()
		else:
			if not self.settings.movies_save:
				return
			base_path = self.settings.movies_path()

		with filesystem.save_make_chdir_context(base_path, 'kinohd_movies'):
			return movieapi.write_movie(parser.get_value('full_title'), url, self.settings, parser, path=base_path)

	def process_tvshow(self, url, parser):
		import tvshowapi
		import filesystem

		api = parser.movie_api()
		genre = api['genres']
		if u'мультфильм' in genre:
			if not self.settings.animation_tvshows_save:
				return
			base_path = self.settings.animation_tvshow_path()
		else:
			if not self.settings.tvshows_save:
				return
			base_path = self.settings.tvshow_path()
		with filesystem.save_make_chdir_context(base_path, 'kinohd_tvshow'):
			return tvshowapi.write_tvshow(parser.get_value('full_title'), url, self.settings, parser, path=base_path)

	def process(self, url, fulltitle):
		parser = DescriptionParser(url, fulltitle, settings=self.settings)
		try:
			parser.Dict()['title']			= parser.movie_api()['title']
			parser.Dict()['originaltitle']	= parser.movie_api()['originaltitle']
		except:
			pass
		if parser.parsed():
			if 'sezon' in url or parser.movie_api().get('type') == 'tvshow':
				return self.process_tvshow(url, parser)
			else:
				return self.process_movie(url, parser)

	def test(self):
		url = 'http://kinohd.net/1080p/7653-3be3916hbiy-928ytb-916uckabepu-1-sezon-1-2-serii-iz-15-star-trek-discovery-2017.html'
		fulltitle = u'3BE3ΔHblҊ ΠYTb: ΔͶCKABEPͶ (1 сезон: 1-15 серии из 15) / Star Trek: Discovery / 2017'
		self.process(url, fulltitle)


def run(settings):
	import filesystem
	types = ['4k', '1080p', '720p', '3d', 'serial']
	items_on_page	= 30
	#all_items_count = len(types) * items_on_page
	processed_urls = []

	def urls():
		for t in types:
			if not getattr(settings, 'kinohd_' + t, False):
				continue

			indx = 0
			for item in PostEnumerator(url(t)).items():
				progress = int(indx * 100 / items_on_page)
				settings.progress_dialog.update(progress, u'KinoHD: {}'.format(t.upper()), item[1])
				indx += 1

				yield item

	process = Process(settings)
	for href, fulltitle in urls():
		if href not in processed_urls:
			process.process(href, fulltitle)
			processed_urls.append(href)


def download_torrent(url, path, settings):
	from base import save_hashes
	save_hashes(path)

	import urllib2
	url = urllib2.unquote(url)
	debug('download_torrent:' + url)

	soup = soup_base(url).soup
	if soup:
		# <button onclick="window.document.location.href='/engine/torrent.php?nid=8280&amp;id=10977'" class="bytn" style="cursor: pointer;" title="скачивание работает с программой Utorrent"> Скачать</button>
		btn = soup.find('button', class_="bytn")
		if btn:
			try:
				dnl_url = btn['onclick']
				dnl_url = dnl_url.split("href=")[-1]
				dnl_url = dnl_url.replace("'", "")
				dnl_url = '{}://{}{}'.format(protocol, domain, dnl_url)
			except BaseException as e:
				pass
			
			import requests
			r = requests.get(dnl_url)

			try:
				import filesystem
				with filesystem.fopen(path, 'wb') as torr:
					for chunk in r.iter_content(100000):
						torr.write(chunk)

				save_hashes(path)
				return True
			except:
				pass

	return False
			

def search_generate(what, imdb, settings, path_out):

	url = '{}://{}'.format(protocol, domain)
	headers = {
		'Host' :		domain,
		'Origin' :		url,
		'Referer' :		url + '/',
		'Upgrade-Insecure-Requests': '1'
	}

	data = {
		'do':			'search',
		'subaction':	'search',
		'story':		str(imdb)
	}

	import requests
	res = requests.post(url + '/', headers=headers, data=data)

	enumerator = BaseEnumerator(res.content)
	count = enumerator.size()

	def urls():
		indx = 0
		for item in enumerator.items():
			progress = int(indx * 100 / count)
			settings.progress_dialog.update(progress, u'KinoHD: поиск', item[1])
			indx += 1

			yield item

	process = Process(settings)
	for href, fulltitle in urls():
		result = process.process(href, fulltitle)
		path_out.append(result) 

	return count


if __name__ == '__main__':
	from settings import Settings
	import filesystem

	test_dir = filesystem.join(filesystem.dirname(__file__), 'test')

	settings = Settings( filesystem.join(test_dir, 'Videos') )
	settings.addon_data_path	= filesystem.join(test_dir, 'data')
	settings.torrent_path		= filesystem.join(test_dir, 'torrents')
	settings.torrent_player		= 'torrent2http'
	settings.kp_googlecache		= False
	settings.kp_usezaborona		= True
	settings.use_kinopoisk		= True
	settings.use_worldart		= True

	#settings.kinohd_4k				= False
	#settings.kinohd_1080p			= False
	#settings.kinohd_720p			= False
	#settings.kinohd_3d				= False

	path_out = []
	#res = search_generate(None, 'tt0898266', settings, path_out)
	run(settings)
	#Process(settings).test()

	pass