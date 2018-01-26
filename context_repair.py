# -*- coding: utf-8 -*-
import sys
from log import debug
from settings import _addon_name

class MyListItem(object):
	def getdescription(self):
		return str()

	def getduration(self):
		import xbmc
		return xbmc.getInfoLabel("ListItem.Duration ") 

	def getfilename(self):
		import xbmc
		return xbmc.getInfoLabel("ListItem.FileName")

	def getLabel(self):
		import xbmc
		return xbmc.getInfoLabel("ListItem.Label")

	def getLabel2(self):
		import xbmc
		return xbmc.getInfoLabel("ListItem.Label2")

	def getProperty(self, key):
		import xbmc
		return xbmc.getInfoLabel("ListItem.Property({})".format(key))

	def getPath(self):
		import xbmc
		return xbmc.getInfoLabel("ListItem.Path")

	def getRating(self, key):
		import xbmc
		return float()

class AskUser(object):
	def __init__(self):
		self._ask_update = None
		self._ask_files_remove = None
		self._progress = None

	def ask_update(self):
		if self._ask_update is None:
			import xbmcgui
			self._ask_update = xbmcgui.Dialog().yesno(_addon_name, u'Обновить описания?')
		return self._ask_update

	def ask_files_remove(self):
		if self._ask_files_remove is None:
			import xbmcgui
			self._ask_files_remove = xbmcgui.Dialog().yesno(_addon_name, u'Удалить файлы?')
		return self._ask_files_remove

	def progress_start(self, count):
		import xbmcgui
		self._progress = xbmcgui.DialogProgressBG()
		self._progress.create(_addon_name)
		self._progress_count = count

	def progress_update(self, current, msg):
		percent = current * 100 / self._progress_count
		self._progress.update(percent, _addon_name, msg)

	def progress_stop(self):
		self._progress.close()

user = AskUser()

def debug_arr(a):
	i = 0
	for e in a:
		debug('{}: {}'.format(i, e))
		i += 1

def executeJSONRPC(q):
	import json, xbmc
	s = json.dumps(q)
	res = xbmc.executeJSONRPC(s)
	return json.loads(res)

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


def remove_tvshow(show_id):
	pass

def ep_id(season, episode):
	return 'S{}E{}'.format(season, episode)

def get_tvshowapi_data(imdb_id):
	from tvshowapi import TheTVDBAPI

	api = TheTVDBAPI(imdb_id)

	data = {}

	for ep in api.tvdb_ru:
		if ep.tag == 'Episode':
			name	= ep.find('EpisodeName').text
			episode = int(ep.find('EpisodeNumber').text)
			season	= int(ep.find('SeasonNumber').text)
			plot	= ep.find('Overview').text

			# VideoLibrary.SetEpisodeDetails compatible 
			# http://kodi.wiki/view/JSON-RPC_API/v8#VideoLibrary.SetEpisodeDetails
			data[ep_id(season, episode)] = {
				'title'		: name,
				'episode'	: episode,
				'season'	: season,
				'plot'		: plot
			}

	return data


def update_episode(e, api_data):

	"""
	playcount, runtime, director, plot, rating, votes, lastplayed, writer,	firstaired, productioncode, season, episode, originaltitle, thumbnail,	fanart, art, resume, userrating, ratings, dateadded,
	"""

	if not user.ask_update():
		return

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

def remove_files(path):
	if path.endswith('.strm'):
		def remove(path):
			import filesystem
			if filesystem.exists(path):
				try:
					filesystem.remove(path)
					debug(u'remove: {}		[OK]'.format(path))
				except:
					debug(u'remove: {}		[Fail]'.format(path))

		remove(path)
		nfo_path = path.replace('.strm', '.nfo')
		remove(nfo_path)
		alt_path = path + '.alternative'
		remove(alt_path)
		

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

	if user.ask_files_remove():
		remove_files(e["file"])

	pass


def repair(tvshow_id):

	tvshow = get_tvshow(tvshow_id)

	tvshows = get_tvshows(tvshow['imdbnumber'])

	for show_id in tvshows:
		if show_id != tvshow['tvshowid']:
			remove_tvshow(show_id)

	episodes = get_episodes(tvshow_id)

	tvshowapi_data = get_tvshowapi_data(tvshow['imdbnumber'])

	user.progress_start(len(episodes))
	index = 1

	for e in episodes:
		epid = ep_id(e['season'], e['episode'])
		if epid in tvshowapi_data:
			update_episode(e, tvshowapi_data[epid])
		else:
			remove_episode(e)

		user.progress_update(index, e["file"])
		index += 1

	user.progress_stop()


def main():
	try:
		li = sys.listitem
	except:
		li = MyListItem()

	path = li.getPath()
	debug(path)

	if path.startswith('videodb://tvshows/titles/'):
		elements = path.split('/')
		debug_arr(elements)

		tvshow_id = elements[4]
		repair(tvshow_id)


if __name__ == '__main__':
	import vsdbg
	vsdbg._bp()

	main()