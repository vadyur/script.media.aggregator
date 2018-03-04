# -*- coding: utf-8 -*-

from base import DescriptionParserBase, Informer
from soup_base import soup_base

class DescriptionParser(DescriptionParserBase, soup_base):
	def __init__(self, url, settings=None):
		Informer.__init__(self)
		soup_base.__init__(self, url)

		self._dict = dict()
		self._dict['link'] = url
		
		self.settings = settings
		self.OK = self.parse()

	def link(self):
		return self._dict['link']

	def parse(self):
		import re
		imdb = self.soup.find('img', class_="imdb_informer")
		if imdb:
			self._dict['imdb_id'] = re.search('(tt\d+)', imdb['src']).group(1)
		kp_a = self.soup.select('a[href*="/class/goo.php?url=http://www.kinopoisk.ru/film/]')
		if kp_a:
			self._dict['kp_id'] = kp_a[0]['href'].split('url=')[-1]

		if self.get_value('imdb_id'):
			self.make_movie_api(self.get_value('imdb_id'), self.get_value('kp_id'), self.settings)
			return True


class PostEnumerator(soup_base):
	def __init__(self, url):
		soup_base.__init__(self, url)

	def items(self):
		div = self.soup.find('div', class_="s5roundwrap")
		if div:
			for a in div.find_all('a'):
				href = a.get('href', '')
				if href.endswith(u'.html'):
					yield a['href']

def url(type):
	return 'http://kinohd.net/{}/'.format(type)

def run(settings):
	types = ['4k', '1080p', '720p', '3d', 'serial']
	processed_urls = []

	def urls():
		for t in types:
			for item in PostEnumerator(url(t)).items():
				yield item

	def process_movie(url, parser):
		import movieapi
		api = parser.movie_api()
		genre = api['genres']
		if u'мультфильм' in genre:
			base_path = settings.animation_path()
		elif u'документальный' in genre:
			base_path = settings.documentary_path()
		else:
			base_path = settings.movies_path()

		movieapi.write_movie(u'', url, settings, parser, path=base_path)

	def process_tvshow(url, parser):
		import tvshowapi
		api = parser.movie_api()
		genre = api['genres']
		if u'мультфильм' in genre:
			base_path = settings.animation_tvshow_path()
		else:
			base_path = settings.tvshow_path()
		tvshowapi.write_tvshow(u'', url, settings, parser, path)

	def process_url(url):
		parser = DescriptionParser(url)
		if parser.parsed():
			if 'sezon' in url:
				procces_tvshow(url, parser)
			else:
				process_movie(url, parser)

	for item in urls():
		if item not in processed_urls:
			process_url(item)
			processed_urls.append(item)

	pass

def download_torrent(url, path, settings):
	pass

def search_generate(what, imdb, settings, path_out):
	pass

if __name__ == '__main__':
	from settings import Settings
	settings = Settings('c:\\Temp')

	run(settings)