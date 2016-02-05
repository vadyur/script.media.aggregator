# -*- coding: utf-8 -*-

import json, re, base
import urllib2, requests
from bs4 import BeautifulSoup

class KinopoiskAPI(object):
	def __init__(self, kinopoisk_url = None):
		self.kinopoisk_url = kinopoisk_url
		self.soup = None

	def getTitle(self):
		title = None
		if self.kinopoisk_url and self.soup is None:
			r = requests.get(self.kinopoisk_url)
			if r.status_code == requests.codes.ok:
				self.soup = BeautifulSoup(base.clean_html(r.text), 'html.parser')

		if self.soup:
			h = self.soup.find('h1', class_ = 'moviename-big')
			if h:
				title = h.contents[0].strip()

		return title

	def Actors(self):
		actors = []
		if self.kinopoisk_url:
			cast_url = self.kinopoisk_url + 'cast/'
			r = requests.get(cast_url)
			if r.status_code == requests.codes.ok:
				soup = BeautifulSoup(base.clean_html(r.text), 'html.parser')
				for a in soup.select('a[name="actor"]'):
					for sibling in a.next_siblings:
						if not hasattr(sibling, 'tag'):
							continue
						if sibling.tag == 'a':
							return actors
						for actorInfo in sibling.select('.actorInfo'):
							photo 		= actorInfo.select('div.photo a')[0]['href']
							#http://st.kp.yandex.net/images/actor_iphone/iphone360_30098.jpg
							#/name/7627/
							photo 		= photo.replace('/', '').replace('name', '')
							photo 		= 'http://st.kp.yandex.net/images/actor_iphone/iphone360_' + photo + '.jpg'
							ru_name		= actorInfo.select('div.info .name a')[0].get_text()
							en_name		= actorInfo.select('div.info .name span')[0].get_text()
							role		= actorInfo.select('div.info .role')[0].get_text().replace('... ', '')
							role 		= role.split(',')[0]
							actors.append({'photo': photo,'ru_name': ru_name,'en_name': en_name,'role': role})
		return actors

	def __trailer(self, element):
		for parent in element.parents:
			#print parent.tag
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
								print 'trailer: ' + trailer
							except:
								pass
							return trailer
		return None

	def Trailer(self):
		if self.kinopoisk_url:
			trailer_page = self.kinopoisk_url + 'video/type/1/'
			r = requests.get(trailer_page)
			if r.status_code == requests.codes.ok:
				soup = BeautifulSoup(base.clean_html(r.text), 'html.parser')
				for div in soup.select('tr td div div.flag2'):
					trailer = self.__trailer(div)
					if trailer:
						return trailer
				for a in soup.select('a.all'):
					return self.__trailer(a)
		return None


class MovieAPI(KinopoiskAPI):
	tmdb_api_key		= '57983e31fb435df4df77afb854740ea9'	# from metadata.common.themoviedb.org scraper
	api_url		= 'https://api.themoviedb.org/3'

	def url_imdb_id(self, idmb_id):
		return 'http://api.themoviedb.org/3/movie/' + idmb_id + '?api_key=' + self.tmdb_api_key + '&language=ru'
		
#	def url_tmdb_images(self, id):
#		return api_url + '/movie/' + id + '/images' + '?api_key=' + self.tmdb_api_key

	def __init__(self, imdb_id = None, kinopoisk = None):
		KinopoiskAPI.__init__(self, kinopoisk)

		if imdb_id:
			url_ = self.url_imdb_id(imdb_id)
			try:
				self.tmdb_data 	= json.load(urllib2.urlopen( url_ ))
				print 'tmdb_data (' + url_ + ') \t\t\t[Ok]'
			except:
				pass

			try:
				omdb_url = 'http://www.omdbapi.com/?i=' + imdb_id + '&plot=short&r=json'
				self.omdbapi	= json.load(urllib2.urlopen( omdb_url ))
				print 'omdbapi (' + omdb_url + ') \t\t\t[Ok]'
			except:
				pass
			

	def imdbRating(self):
		return self.omdbapi['imdbRating']
		
	def Runtime(self):
		return self.omdbapi['Runtime'].encode('utf-8').replace(' min', '')
		
	def Rated(self):
		return self.omdbapi.get(u'Rated', u'')

	def Poster(self):
		return self.omdbapi.get(u'Poster', u'')
		
	def Collection(self):                           
		try:
			if u'belongs_to_collection' in self.tmdb_data:
				belongs_to_collection = self.tmdb_data[u'belongs_to_collection']
				if u'name' in belongs_to_collection:
					return belongs_to_collection[u'name']
		except:
			pass
			
		return u''
		
	def Tags(self):
		tags = []
		try:
			if u'tagline' in self.tmdb_data:
				tagline = self.tmdb_data[u'tagline']
				for tag in tagline.split(','):
					tag = tag.strip()
					if len(tag) > 0:
						tags.append(tag)
		except:
			pass
			
		return tags

	def __getitem__(self, key):
		return self.tmdb_data[key]

