# -*- coding: utf-8 -*-


import operator
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from torrent2http import Error as TPError

import anidub
import nnmclub
import tvshowapi
from base import STRMWriterBase
from downloader import TorrentDownloader
from kodidb import *
from nforeader import NFOReader
from settings import *
from torrent2httpplayer import *
from yatpplayer import *
from movieapi import MovieAPI

# Определяем параметры плагина
_ADDON_NAME = 'script.media.aggregator'
_addon = xbmcaddon.Addon(id=_ADDON_NAME)
_addon_path = _addon.getAddonInfo('path').decode('utf-8')

try:
	_addondir = xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')
except:
	_addondir = u''

debug(_addondir.encode('utf-8'))


def get_params():
	param = dict()

	paramstring = sys.argv[2]
	if len(paramstring) >= 2:
		params = sys.argv[2]
		cleanedparams = params.replace('?', '')
		if (params[len(params) - 1] == '/'):
			params = params[0:len(params) - 2]
		pairsofparams = cleanedparams.split('&')
		param = {}
		for i in range(len(pairsofparams)):
			splitparams = {}
			splitparams = pairsofparams[i].split('=')
			if (len(splitparams)) == 2:
				param[splitparams[0]] = splitparams[1]

	# debug(param)
	return param


def getSetting(id, default=''):
	result = _addon.getSetting(id)
	if result != '':
		return result
	else:
		return default


def load_settings():
	# import rpdb2
	# rpdb2.start_embedded_debugger('pw')

	base_path = getSetting('base_path', '').decode('utf-8')
	if base_path == u'Videos':
		base_path = filesystem.join(_addondir, base_path)

	movies_path = getSetting('movies_path', 'Movies').decode('utf-8')
	animation_path = getSetting('animation_path', 'Animation').decode('utf-8')
	documentary_path = getSetting('documentary_path', 'Documentary').decode('utf-8')
	anime_path = getSetting('anime_path', 'Anime').decode('utf-8')

	hdclub_passkey = getSetting('hdclub_passkey')
	anidub_login = getSetting('anidub_login')
	anidub_password = getSetting('anidub_password')

	nnmclub_pages = 3
	nnmclub_login = getSetting('nnmclub_login')
	nnmclub_password = getSetting('nnmclub_password')

	rutor_domain = getSetting('rutor_domain')
	rutor_filter = getSetting('rutor_filter')

	preffered_bitrate = int(getSetting('preffered_bitrate'))
	preffered_type = getSetting('preffered_type')

	torrent_player = getSetting('torrent_player')
	storage_path = getSetting('storage_path')

	movies_save = getSetting('movies_save') == 'true'
	animation_save = getSetting('animation_save') == 'true'
	documentary_save = getSetting('documentary_save') == 'true'
	anime_save = getSetting('anime_save') == 'true'
	tvshows_save = getSetting('tvshows_save') == 'true'
	animation_tvshows_save = getSetting('animation_tvshows_save') == 'true'

	torrent_path = getSetting('torrent_path')

	settings = Settings(base_path,
	                    movies_path=movies_path,
	                    animation_path=animation_path, documentary_path=documentary_path,
	                    anime_path		=anime_path,
	                    hdclub_passkey 		=hdclub_passkey,
	                    anidub_login 		=anidub_login,
	                    anidub_password 	=anidub_password,
	                    nnmclub_pages 		=nnmclub_pages,
	                    nnmclub_login 		=nnmclub_login,
	                    nnmclub_password 	=nnmclub_password,
	                    rutor_domain        =rutor_domain,
	                    rutor_filter        =rutor_filter,
	                    preffered_bitrate 	=preffered_bitrate,
	                    preffered_type 		=preffered_type,
	                    torrent_player 		=torrent_player,
	                    storage_path		=storage_path,
	                    movies_save 		=movies_save,
	                    animation_save 		=animation_save,
	                    documentary_save 	=documentary_save,
	                    anime_save 			=anime_save,
	                    tvshows_save 		=tvshows_save,
	                    animation_tvshows_save =animation_tvshows_save,
	                    torrent_path        =torrent_path)

	settings.addon_data_path		= _addondir
	if getSetting('data_path'):
		settings.addon_data_path    = getSetting('data_path')

	settings.run_script				= getSetting('run_script') == 'true'
	settings.script_params			= getSetting('script_params').decode('utf-8')

	settings.move_video             = getSetting('action_files').decode('utf-8') == u'переместить'
	settings.remove_files           = getSetting('action_files').decode('utf-8') == u'удалить'
	settings.copy_video_path        = getSetting('copy_video_path').decode('utf-8')

	settings.copy_torrent           = getSetting('copy_torrent') == 'true'
	settings.copy_torrent_path      = getSetting('copy_torrent_path').decode('utf-8')

	return settings


def play_torrent_variant(path, info_dialog, episodeNumber, nfoReader, settings, params, downloader):
	import filecmp

	play_torrent_variant. resultOK 		= 'OK'
	play_torrent_variant. resultCancel 	= 'Cancel'
	play_torrent_variant. resultTryNext	= 'TryNext'
	play_torrent_variant. resultTryAgain	= 'TryAgain'

	# import rpdb2
	# rpdb2.start_embedded_debugger('pw')

	start_time = time.time()
	start_play_max_time 	= int(_addon.getSetting(  'start_play_max_time'))	  # default 60 seconds
	search_seed_max_time = int(_addon.getSetting('search_seed_max_time'))  # default 15 seconds

	if episodeNumber != None:
		episodeNumber = int(episodeNumber)

	if settings == None:
		return play_torrent_variant.resultCancel

	if downloader:
		downloader.start(True)

	torrent_info = None
	torrent_path = path

	try:
		if settings.torrent_player == 'YATP':
			player = YATPPlayer()
		elif settings.torrent_player == 'torrent2http':
			player = Torrent2HTTPPlayer(settings)
		elif settings.torrent_player == 'Ace Stream':
			import aceplayer
			player = aceplayer.AcePlayer(settings)

		debug('------------ Open torrent: ' + path)
		player.AddTorrent(path)

		added = False
		for i in range(start_play_max_time):
			if player.CheckTorrentAdded():
				added = True
				break

			if xbmc.abortRequested:
				return play_torrent_variant.resultCancel

			info_dialog.update(i, u'Проверяем файлы', ' ', ' ')

			if downloader and downloader.is_finished():
				if not filecmp.cmp(path, downloader.get_filename()):
					downloader.move_file_to(path)
					debug('play_torrent_variant.resultTryAgain')
					return play_torrent_variant.resultTryAgain
				else:
					debug('Torrents are equal')
					downloader = None

			xbmc.sleep(1000)

		if not added:
			debug('Torrent not added')
			return play_torrent_variant.resultTryNext

		files = player.GetLastTorrentData()['files']
		debug(files)

		if 'cutName' not in params:
			if 'index' not in params:
				if episodeNumber is not None:
					files.sort(key=operator.itemgetter('name'))
				else:
					files.sort(key=operator.itemgetter('size'), reverse=True)
				debug('sorted_files:')
				debug(files)

		try:		
			if 'cutName' not in params:
				if 'index' not in params:
					if episodeNumber is None:
						index = 0
						playable_item = files[0]
					else:
						playable_item = files[episodeNumber]
						index = playable_item.get('index')
				else:
					index = -1
					for item in files:
						if int(params['index']) == item['index']:
							playable_item = item
							index = playable_item.get('index')
			else:
				cutName = urllib.unquote(params['cutName']).decode('utf-8').lower()
				index = -1
				for item in files:
					name = item['name'].lower()
					if cutName in unicode(tvshowapi.cutStr(name)):
						playable_item = item
						index = playable_item.get('index')
						break

				if index == -1:
					return play_torrent_variant.resultTryNext
		except IndexError:
			for i in range(10):
				if downloader and downloader.is_finished():
					if not filecmp.cmp(path, downloader.get_filename()):
						downloader.move_file_to(path)
						print 'play_torrent_variant.resultTryAgain'
						return play_torrent_variant.resultTryAgain
				xbmc.sleep(1000)

		debug(playable_item)

		player.StartBufferFile(index)

		if not player.CheckTorrentAdded():
			info_dialog.update(0, 'Media Aggregator: проверка файлов')

		while not info_dialog.iscanceled() and not player.CheckTorrentAdded():
			xbmc.sleep(1000)
			start_time = time.time()

		info_dialog.update(0, 'Media Aggregator: буфферизация')

		while not info_dialog.iscanceled():
			if player.CheckBufferComplete():
				break

			percent = player.GetBufferingProgress()
			if percent >= 0:
				player.updateDialogInfo(percent, info_dialog)

			if time.time() > start_time + start_play_max_time:
				return play_torrent_variant.resultTryNext

			if time.time() > start_time + search_seed_max_time:
				info = player.GetTorrentInfo()
				if 'num_seeds' in info:
					if info['num_seeds'] == 0:
						debug('Seeds not found')
						return play_torrent_variant.resultTryNext

			if downloader and downloader.is_finished():
				if not filecmp.cmp(path, downloader.get_filename()):
					downloader.move_file_to(path)
					debug('play_torrent_variant.resultTryAgain')
					return play_torrent_variant.resultTryAgain
				else:
					debug('Torrents are equal')
					downloader = None

			xbmc.sleep(1000)

		canceled = info_dialog.iscanceled()
		info_dialog.update(0)
		info_dialog.close()
		if canceled:
			return play_torrent_variant.resultCancel

		playable_url = player.GetStreamURL(playable_item)
		debug(playable_url)

		handle = int(sys.argv[1])
		if nfoReader != None:
			list_item = nfoReader.make_list_item(playable_url)
		else:
			list_item = xbmcgui.ListItem(path=playable_url)

		rel_path = urllib.unquote(params['path']).decode('utf-8')
		filename = urllib.unquote(params['nfo']).decode('utf-8')

		k_db = KodiDB(filename.replace(u'.nfo', u'.strm'), \
		              rel_path,
		              sys.argv[0] + sys.argv[2])
		k_db.PlayerPreProccessing()

		xbmc_player = xbmc.Player()
		xbmcplugin.setResolvedUrl(handle, True, list_item)

		while not xbmc_player.isPlaying():
			xbmc.sleep(300)

		debug('!!!!!!!!!!!!!!!!! Start PLAYING !!!!!!!!!!!!!!!!!!!!!')

		if k_db.timeOffset != 0:
			debug("Seek to time: " + str(k_db.timeOffset))
			xbmc.sleep(2000)
			xbmc_player.seekTime(int(k_db.timeOffset))

		# Wait until playing finished or abort requested
		while not xbmc.abortRequested and xbmc_player.isPlaying():
			player.loop()
			xbmc.sleep(1000)

		debug('!!!!!!!!!!!!!!!!! END PLAYING !!!!!!!!!!!!!!!!!!!!!')

		xbmc.sleep(1000)

		# import rpdb2
		# rpdb2.start_embedded_debugger('pw')

		k_db.PlayerPostProccessing()

		torrent_info = player.GetTorrentInfo()
		torrent_path = player.path
		info_hash = player.GetLastTorrentData()['info_hash']

		xbmc.executebuiltin('Container.Refresh')
		UpdateLibrary_path = filesystem.join(settings.base_path(), rel_path).encode('utf-8')
		log.debug(UpdateLibrary_path)
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video", "%s", "false")' % UpdateLibrary_path)

	except TPError as e:
		log.print_tb(e)
		return play_torrent_variant.resultTryNext

	finally:
		player.close()

	if settings.run_script or settings.remove_files or settings.move_video or settings.copy_torrent:
		import afteractions
		afteractions.Runner(settings, params, playable_item, torrent_info, torrent_path, info_hash)

	return play_torrent_variant.resultOK


def get_path_or_url_and_episode(settings, params, torrent_source):
	tempPath = xbmc.translatePath('special://temp').decode('utf-8')
	torr_downloader = TorrentDownloader(urllib.unquote(torrent_source), tempPath, settings)

	path = filesystem.join(settings.torrents_path(), torr_downloader.get_subdir_name(),
	                       torr_downloader.get_post_index() + '.torrent')
	if not filesystem.exists(path):
		torr_downloader.download()
		torr_downloader.move_file_to(path)
		torr_downloader = None

	return {'path_or_url': path, 'episode': params.get('episodeNumber', None), 'downloader': torr_downloader}


def openInTorrenter(nfoReader):
	try:
		xbmcaddon.Addon(id='plugin.video.torrenter')
	except:
		return

	if not nfoReader is None:
		info = nfoReader.get_info()
		ctitle = None
		if 'title' in info:
			ctitle = info['title']
		elif 'originaltitle' in info:
			ctitle = info['originaltitle']
		if not ctitle is None:
			uri = \
				'%s?%s' % (
				'plugin://plugin.video.torrenter/', urllib.urlencode({'action': 'search', 'url': ctitle.encode('utf-8')}))
			debug('Search in torrenter: ' + uri)
			xbmc.executebuiltin(b'Container.Update(\"%s\")' % uri)


def play_torrent(settings, params):
	info_dialog = xbmcgui.DialogProgress()
	info_dialog.create('Media Aggregator')

	tempPath = xbmc.translatePath('special://temp').decode('utf-8')
	base_path = settings.base_path().encode('utf-8')
	rel_path = urllib.unquote(params.get('path', ''))
	nfoFilename = urllib.unquote(params.get('nfo', ''))
	nfoFullPath = NFOReader.make_path(base_path, rel_path, nfoFilename)
	strmFilename = nfoFullPath.replace('.nfo', '.strm')
	nfoReader = NFOReader(nfoFullPath, tempPath) if filesystem.exists(nfoFullPath) else None

	debug(strmFilename.encode('utf-8'))
	links_with_ranks = STRMWriterBase.get_links_with_ranks(strmFilename, settings, use_scrape_info=True)

	anidub_enable = _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable = _addon.getSetting('hdclub_enable') == 'true'
	nnmclub_enable = _addon.getSetting('nnmclub_enable') == 'true'
	rutor_enable = _addon.getSetting('rutor_enable') == 'true'

	onlythis = False
	if 'onlythis' in params and params['onlythis'] == 'true':
		onlythis = True

	for v in links_with_ranks[:]:
		# if v['link'] in sys.argv[0] + sys.argv[2]:
		#	links_with_ranks.remove(v)
		if not anidub_enable and 'tr.anidub.com' in v['link']:
			links_with_ranks.remove(v)
		if not hdclub_enable and 'hdclub.org' in v['link']:
			links_with_ranks.remove(v)
		if not nnmclub_enable and 'nnm-club.me' in v['link']:
			links_with_ranks.remove(v)
		if not rutor_enable and 'rutor.info' in v['link']:
			links_with_ranks.remove(v)

	debug('links_with_ranks: ' + str(links_with_ranks))

	if len(links_with_ranks) == 0 or onlythis:
		torrent_source = params['torrent']
		path_or_url_and_episode = get_path_or_url_and_episode(settings, params, torrent_source)
		if path_or_url_and_episode:
			path = path_or_url_and_episode['path_or_url']
			episodeNumber = path_or_url_and_episode['episode']
			downloader = path_or_url_and_episode['downloader']
			play_torrent_variant_result = play_torrent_variant(path, info_dialog, episodeNumber, nfoReader, settings,
			                                                   params, downloader)
			if play_torrent_variant_result == play_torrent_variant.resultTryAgain:
				play_torrent_variant_result = play_torrent_variant(path, info_dialog, episodeNumber, nfoReader,
				                                                   settings, params, None)
	else:
		for tryCount, variant in enumerate(links_with_ranks, 1):

			if tryCount > 1:
				info_dialog.update(0, 'Media Aggregator', 'Попытка #%d' % tryCount)
			debug(variant)

			torrent_source = variant['link']
			try:
				torrent_source = torrent_source.split('torrent=')[1].split('&')[0]
			except:
				continue

			path_or_url_and_episode = get_path_or_url_and_episode(settings, params, torrent_source)
			if path_or_url_and_episode is None:
				continue

			episodeNumber = path_or_url_and_episode['episode']
			downloader = path_or_url_and_episode['downloader']

			play_torrent_variant_result = play_torrent_variant(path_or_url_and_episode['path_or_url'], info_dialog,
			                                                   episodeNumber, nfoReader, settings, params, downloader)
			if play_torrent_variant_result == play_torrent_variant.resultTryAgain:
				play_torrent_variant_result = play_torrent_variant(path_or_url_and_episode['path_or_url'], info_dialog,
				                                                   episodeNumber, nfoReader, settings, params, None)

			if play_torrent_variant_result != play_torrent_variant.resultTryNext:
				break

	info_dialog.update(0, '', '')
	info_dialog.close()

	if play_torrent_variant_result == play_torrent_variant.resultTryNext and not onlythis:
		# Open in torrenter
		openInTorrenter(nfoReader)


restart_msg = u'Чтобы изменения вступили в силу, нужно перезапустить KODI. Перезапустить?'


def check_sources(settings):
	import sources
	if sources.need_create(settings):
		dialog = xbmcgui.Dialog()
		if dialog.yesno('Media Aggregator', u'Источники категорий не созданы. Создать?'):
			if sources.create(settings):
				if dialog.yesno('Media Aggregator', restart_msg):
					xbmc.executebuiltin('Quit')
			return True
		else:
			return False

	return True


class dialog_action_case:
	generate = 0
	sources = 1
	settings = 2
	search = 3
	catalog = 4
	exit = 5


def dialog_action(action, settings):
	# import rpdb2
	# rpdb2.start_embedded_debugger('pw')


	if action == dialog_action_case.generate:
		anidub_enable = _addon.getSetting('anidub_enable') == 'true'
		hdclub_enable = _addon.getSetting('hdclub_enable') == 'true'
		nnmclub_enable = _addon.getSetting('nnmclub_enable') == 'true'
		rutor_enable = _addon.getSetting('rutor_enable') == 'true'

		if not (anidub_enable or hdclub_enable or nnmclub_enable or rutor_enable):
			xbmcgui.Dialog().ok(_ADDON_NAME, u'Пожалуйста, заполните настройки', u'Ни одного сайта не выбрано')
			action = dialog_action_case.settings
		else:
			from service import start_generate
			# if check_sources(settings):
			start_generate()
			return True

	if action == dialog_action_case.sources:
		# import rpdb2
		# rpdb2.start_embedded_debugger('pw')

		import sources

		# sources.create(settings)
		dialog = xbmcgui.Dialog()
		if sources.create(settings):
			if dialog.yesno('Media Aggregator', restart_msg):
				from service import update_library_next_start

				update_library_next_start()
				xbmc.executebuiltin('Quit')

	if action == dialog_action_case.settings:
		save_nnmclub_login = settings.nnmclub_login
		save_nnmclub_password = settings.nnmclub_password
		_addon.openSettings()
		settings = load_settings()

		if save_nnmclub_login != settings.nnmclub_login or save_nnmclub_password != settings.nnmclub_password:
			passkey = nnmclub.get_passkey(settings=settings)
			_addon.setSetting('nnmclub_passkey', passkey)
			settings.nnmclub_passkey = passkey

	if action == dialog_action_case.search:

		dlg = xbmcgui.Dialog()
		s = dlg.input(u'Введите поисковую строку')

		if s:
			debug(s)
			show_list(MovieAPI.search(s.decode('utf-8')))

	if action == dialog_action_case.catalog:
		addon_handle = int(sys.argv[1])
		xbmcplugin.setContent(addon_handle, 'movies')

		listing = {

			'popular': u'Популярные',
			'top_rated': u'Рейтинговые',
			'popular_tv': u'Популярные сериалы',
			'top_rated_tv': u'Рейтинговые сериалы'
		}

		for l in listing:
			li = xbmcgui.ListItem(listing[l])
			li.setProperty("folder", "true")
			li.setProperty('IsPlayable', 'false')

			url = 'plugin://script.media.aggregator/?action=show_category&category=' + l
			debug(url)
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

		xbmcplugin.endOfDirectory(addon_handle)

	if action > dialog_action_case.settings or action < dialog_action_case.generate:
		return True

	return False


def show_list(listing):
	addon_handle = int(sys.argv[1])
	xbmcplugin.setContent(addon_handle, 'movies')
	for item in listing:
		info = item.get_info()
		li = xbmcgui.ListItem(info['title'])
		li.setInfo('video', info)
		li.setArt(item.get_art())

		url = 'plugin://script.media.aggregator/?' + urllib.urlencode(
			{'action': 'add_media',
			 'title': info['title'].encode('utf-8'),
			 'imdb': item.imdb()})

		li.addContextMenuItems([
			#(u'Смотрите также', 'ActivateWindow(Video,"plugin://script.media.aggregator/?action=show_similar&tmdb=%s", return)' % str(item.tmdb_id())),
			(u'Смотрите также', 'Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % str(item.tmdb_id())),
		])

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
	xbmcplugin.endOfDirectory(addon_handle)


def main():
	from service import create_mark_file
	create_mark_file()

	params = get_params()
	debug(params)
	settings = load_settings()

	xbmc.log(settings.base_path())
	if 'torrent' in params:
		# import rpdb2
		# rpdb2.start_embedded_debugger('pw')
		play_torrent(settings=settings, params=params)

	elif params.get('action') == 'anidub-add-favorites':
		debug('anidub-add-favorites')
		anidub_enable = _addon.getSetting('anidub_enable') == 'true'
		if anidub_enable:
			if settings.anime_save:
				debug('scan for anidub-add-favorites')
				anidub.write_favorites(settings.anime_tvshow_path(), settings)

	elif params.get('action') == 'settings':
		dialog_action(dialog_action_case.settings, settings)

	elif params.get('action') == 'search':
		dialog_action(dialog_action_case.search, settings)

	elif params.get('action') == 'search_context':
		s = params.get('s')
		show_list(MovieAPI.search(s.decode('utf-8')))

	elif params.get('action') == 'catalog':
		dialog_action(dialog_action_case.catalog, settings)

	elif params.get('action') == 'show_category':
		if params.get('category') == 'popular':
			show_list(MovieAPI.popular())
		if params.get('category') == 'top_rated':
			show_list(MovieAPI.top_rated())
		if params.get('category') == 'popular_tv':
			show_list(MovieAPI.popular_tv())
		if params.get('category') == 'top_rated_tv':
			show_list(MovieAPI.top_rated_tv())

	elif params.get('action') == 'show_similar':
		listing = MovieAPI.show_similar(params.get('tmdb'))
		log.debug(listing)
		show_list(listing)

	elif params.get('action') == 'add_media':
		title = urllib.unquote_plus(params.get('title')).decode('utf-8')
		imdb = params.get('imdb')

		import json
		found = None

		# import rpdb2
		# rpdb2.start_embedded_debugger('pw')

		req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]}, "id": "libMovies"}
		result = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
		for r in result['result']['movies']:
			if r['imdbnumber'] == imdb:
				found = 'movie'
				break

		if not found:
			req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]}, "id": "libTvShows"}
			result = json.loads(xbmc.executeJSONRPC(json.dumps(req)))

			for r in result['result']['tvshows']:
				if r['imdbnumber'] == imdb:
					found = 'tvshow'
					break

		dialog = xbmcgui.Dialog()
		if found == 'movie':
			if dialog.yesno(u'Кино найдено в библиотеке', u'Запустить?'):
				#with filesystem.fopen(r['file'], 'r') as strm:
				#	xbmc.executebuiltin('RunPlugin("%s")' % strm.read())
				xbmc.executebuiltin('PlayMedia("%s")' % r['file'].encode('utf-8'))
		elif found == 'tvshow':
			if dialog.yesno(u'Сериал найден в библиотеке', u'Перейти?'):
				xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % r['file'].encode('utf-8'))
		elif not params.get('norecursive'):
			if dialog.yesno(u'Кино/сериал не найден в библиотеке', u'Запустить поиск по трекерам?'):
				from service import add_media
				add_media(title, imdb)

	else:
		menu_items = [u'Генерировать .strm и .nfo файлы',
		              u'Создать источники',
		              u'Настройки',
		              u'Поиск',
		              u'Каталог'
		]
		menu_actions = ['generate',
		                'sources',
						'settings',
						'search',
						'catalog'
		]

		if params.get('menu') in menu_actions:
			dialog_action(menu_actions.index(params.get('menu')), settings)
		else:
			indx = 0
			addon_handle = int(sys.argv[1])
			for menu in menu_items:
				li = xbmcgui.ListItem(menu)
				url = 'plugin://script.media.aggregator/?menu=' + menu_actions[indx]
				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=indx > dialog_action_case.settings)
				indx += 1

			xbmcplugin.endOfDirectory(addon_handle)

		'''
		while True:
			dialog = xbmcgui.Dialog()
			action = dialog.select(u'Выберите опцию:', menu_items)

			if dialog_action(action, settings):
				break
		'''

if __name__ == '__main__':
	main()
