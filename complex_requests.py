from kodidb import MoreRequests

def get_movies_by_imdb(imdb):
	db = MoreRequests()
	res = db.get_movies_by_imdb(imdb)
	def movie(item):
		from log import debug
		debug(unicode(item))

		return {
			'movieid': item['idMovie'],
			'fileid': item['idFile'],
			'title': item['c00'],
			'originaltitle': item['c16'],
			'imdbnumber': item['uniqueid_value'],
			'file': item['c22'],
			'year': item['premiered']
		}

	movies = [movie(item) for item in res]
	return { 'movies': movies }
