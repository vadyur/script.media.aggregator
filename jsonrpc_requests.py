# -*- coding: utf-8 -*-

def executeJSONRPC(q):
	import json, xbmc
	s = json.dumps(q)
	res = xbmc.executeJSONRPC(s)
	return json.loads(res)

class JSONRPC_API(object):
	def __init__(self, name):
		self._name = name

	def __getattribute__(self, name):
		_name = object.__getattribute__(self, '_name')
		def run(limits={}, sort={}, filter={}, **params):
			q = {	"jsonrpc": "2.0",
					"method": _name + "." + name, 
					"params": params,
					"id": "JSONRPC_API"
			}

			if limits:
				q['limits'] = limits
			if sort:
				q['sort'] = sort
			if filter:
				q['filter'] = filter

			try:
				res = executeJSONRPC(q)
				return res['result']
			except KeyError:
				return {}
		return run

VideoLibrary	= JSONRPC_API('VideoLibrary')
JSONRPC			= JSONRPC_API('JSONRPC')
GUI				= JSONRPC_API('GUI')
		
def remove_movie_by_id(id):
	r = VideoLibrary.RemoveMovie(movieid=id)
	pass

def update_movie_by_id(self, id, fields={}):
	params = fields.copy()
	params['movieid'] = id
	r = VideoLibrary.SetMovieDetails(**params)

def get_tvshow(tvshow_id):
	res = VideoLibrary.GetTVShowDetails(tvshowid=int(tvshow_id), 
				properties=["title", "originaltitle", "year", "file", "imdbnumber"])
				
	if 'tvshowdetails' in res:
		return res['tvshowdetails']
	return res

def get_episodes(tvshow_id):
	result = VideoLibrary.GetEpisodes( 
				tvshowid=int(tvshow_id),
				properties=["season", "episode", "file"])

	try:
		return result['episodes']
	except KeyError:
		return []

def get_tvshows(imdb_id):
	result = VideoLibrary.GetTVShows(properties=["imdbnumber"])
	for show in result['tvshows']:
		if show["imdbnumber"] == imdb_id:
			yield show['tvshowid'] 

def update_episode(e, api_data):

	"""
	playcount, runtime, director, plot, rating, votes, lastplayed, writer,	firstaired, productioncode, season, episode, originaltitle, thumbnail,	fanart, art, resume, userrating, ratings, dateadded,
	"""

	params = {'episodeid': e['episodeid']}
	for key in ['title', 'plot']:
		params[key] = api_data[key]

	result = VideoLibrary.SetEpisodeDetails(**params)
	pass

def remove_episode(e):
	# VideoLibrary.RemoveEpisode
	# http://kodi.wiki/view/JSON-RPC_API/v8#VideoLibrary.RemoveEpisode
	result = VideoLibrary.RemoveEpisode(episodeid=e['episodeid'])
