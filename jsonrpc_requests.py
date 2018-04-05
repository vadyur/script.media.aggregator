# -*- coding: utf-8 -*-

def executeJSONRPC(q):
	import json, xbmc
	s = json.dumps(q)
	res = xbmc.executeJSONRPC(s)
	return json.loads(res)

class JSONRPC_API(object):
	def __init__(self, name):
		self.name = name

	def __getattribute__(self, name):
		__name = object.__getattribute__(self, 'name')
		def run(params={}):
			q = {	"jsonrpc": "2.0",
					"method": __name + "." + name, 
					"params": params,
					"id": "tvshow"
			}

			try:
				res = executeJSONRPC(q)
				return res['result']
			except KeyError:
				return {}
		return run

VideoLibrary = JSONRPC_API('VideoLibrary')
JSONRPC = JSONRPC_API('JSONRPC')
		
def remove_movie_by_id(id):
	r = VideoLibrary.RemoveMovie({'movieid': id})
	pass

def update_movie_by_id(self, id, fields={}):
	params = fields.copy()
	params['movieid'] = id
	r = VideoLibrary.SetMovieDetails(params)

def get_tvshow(tvshow_id):
	q = {	"jsonrpc": "2.0",
			"method": "VideoLibrary.GetTVShowDetails", 
			"params": {
				"tvshowid": int(tvshow_id),
				"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]},
			"id": "tvshow"
	}

	try:
		return executeJSONRPC(q)['result']['tvshowdetails']
	except KeyError:
		return {}

def get_episodes(tvshow_id):
	q = {	"jsonrpc": "2.0",
			"method": "VideoLibrary.GetEpisodes", 
			"params": {
				"tvshowid": int(tvshow_id),
				"properties": ["season", "episode", "file"]},
			"id": "episodes"
	}

	try:
		return executeJSONRPC(q)['result']['episodes']
	except KeyError:
		return []

def get_tvshows(imdb_id):
	q = {	"jsonrpc": "2.0",
			"method": "VideoLibrary.GetTVShows", 
			"params": {
				"properties": ["imdbnumber"]},
			"id": "tvshow"
	}

	r = executeJSONRPC(q)

	for show in r['result']['tvshows']:
		if show["imdbnumber"] == imdb_id:
			yield show['tvshowid'] 

def update_episode(e, api_data):

	"""
	playcount, runtime, director, plot, rating, votes, lastplayed, writer,	firstaired, productioncode, season, episode, originaltitle, thumbnail,	fanart, art, resume, userrating, ratings, dateadded,
	"""

	params = {
		'episodeid': e['episodeid']
	}

	for key in ['title', 'plot']:
		params[key] = api_data[key]

	q = {
		"jsonrpc": "2.0",
		"method": 'VideoLibrary.SetEpisodeDetails',
		'params': params,
		"id": "episode_details"
	}

	r = executeJSONRPC(q)
	pass

def remove_episode(e):
	# VideoLibrary.RemoveEpisode
	# http://kodi.wiki/view/JSON-RPC_API/v8#VideoLibrary.RemoveEpisode
	
	params = {
		'episodeid': e['episodeid']
	}

	q = {
		"jsonrpc": "2.0",
		"method": 'VideoLibrary.RemoveEpisode',
		'params': params,
		"id": "episode_details"
	}

	r = executeJSONRPC(q)
