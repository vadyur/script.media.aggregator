from kodidb import MoreRequests

def get_movies_by_imdb(imdb):
	db = MoreRequests()
	res = db.get_movies_by_imdb(imdb)
	def movie(item):
		return {
			'movieid': item[0],
			'fileid': item[1],
			'title': item[2],
			'originaltitle': item[5],
			'imdbnumber': item[4],
			'file': item[3],
			'year': item[6]
		}

	movies = [movie(item) for item in res]
	return {
		'result': {
			'movies': movies
		}
	}