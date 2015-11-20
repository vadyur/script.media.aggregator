import json
import urllib2

class MovieAPI:
	tmdb_api_key		= '57983e31fb435df4df77afb854740ea9'	# from metadata.common.themoviedb.org scraper
	api_url		= 'https://api.themoviedb.org/3'

	def url_imdb_id(self, idmb_id):
		return 'http://api.themoviedb.org/3/movie/' + idmb_id + '?api_key=' + self.tmdb_api_key + '&language=ru'
		
#	def url_tmdb_images(self, id):
#		return api_url + '/movie/' + id + '/images' + '?api_key=' + self.tmdb_api_key

	def __init__(self, imdb_id):
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
		
	def Collection(self):                           
		try:
			if u'belongs_to_collection' in self.tmdb_data:
				belongs_to_collection = self.tmdb_data[u'belongs_to_collection']
				if u'name' in belongs_to_collection:
					return belongs_to_collection[u'name']
		except:
			pass
			
		return u''

	def __getitem__(self, key):
		return self.tmdb_data[key]	
