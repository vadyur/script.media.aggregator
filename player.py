# -*- coding: utf-8 -*-

import operator
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from log import debug, print_tb
import filesystem
import urllib, time

# Определяем параметры плагина
_ADDON_NAME = 'script.media.aggregator'
_addon = xbmcaddon.Addon(id=_ADDON_NAME)
_addon_path = _addon.getAddonInfo('path').decode('utf-8')

try:
	_addondir = xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')
except:
	_addondir = u''

debug(_addondir.encode('utf-8'))


def getSetting(id, default=''):
	result = _addon.getSetting(id)
	if result != '':
		return result
	else:
		return default


def load_settings():
	base_path = getSetting('base_path', '').decode('utf-8')
	if base_path == u'Videos':
		base_path = filesystem.join(_addondir, base_path)

	movies_path = getSetting('movies_path', 'Movies').decode('utf-8')
	animation_path = getSetting('animation_path', 'Animation').decode('utf-8')
	documentary_path = getSetting('documentary_path', 'Documentary').decode('utf-8')
	anime_path = getSetting('anime_path', 'Anime').decode('utf-8')

	hdclub_passkey = getSetting('hdclub_passkey')
	bluebird_passkey = getSetting('bluebird_passkey')
	anidub_login = getSetting('anidub_login')
	anidub_password = getSetting('anidub_password')
	anidub_rss = getSetting('anidub_rss')
	anidub_favorite = getSetting('anidub_favorite')

	nnmclub_pages = 3
	nnmclub_login = getSetting('nnmclub_login')
	nnmclub_password = getSetting('nnmclub_password')

	rutor_domain = getSetting('rutor_domain')
	rutor_filter = getSetting('rutor_filter')

	soap4me_login = getSetting('soap4me_login')
	soap4me_password = getSetting('soap4me_password')
	soap4me_rss = getSetting('soap4me_rss')

	preffered_bitrate = int(getSetting('preffered_bitrate'))
	preffered_type = getSetting('preffered_type')
	preffered_codec = getSetting('preffered_codec')

	torrent_player = getSetting('torrent_player')
	storage_path = getSetting('storage_path')

	movies_save = getSetting('movies_save') == 'true'
	animation_save = getSetting('animation_save') == 'true'
	documentary_save = getSetting('documentary_save') == 'true'
	anime_save = getSetting('anime_save') == 'true'
	tvshows_save = getSetting('tvshows_save') == 'true'
	animation_tvshows_save = getSetting('animation_tvshows_save') == 'true'

	torrent_path = getSetting('torrent_path')

	kp_googlecache = getSetting('kp_googlecache') == 'true'
	rutor_nosd = getSetting('rutor_nosd') == 'true'

	from settings import Settings
	settings = Settings(base_path,
	                    movies_path=movies_path,
	                    animation_path=animation_path, documentary_path=documentary_path,
	                    anime_path		=anime_path,
	                    hdclub_passkey 		=hdclub_passkey,
	                    bluebird_passkey 	=bluebird_passkey,
	                    anidub_login 		=anidub_login,
	                    anidub_password 	=anidub_password,
	                    anidub_rss 	        =anidub_rss,
	                    anidub_favorite 	=anidub_favorite,
	                    nnmclub_pages 		=nnmclub_pages,
	                    nnmclub_login 		=nnmclub_login,
	                    nnmclub_password 	=nnmclub_password,
	                    rutor_domain        =rutor_domain,
	                    rutor_filter        =rutor_filter,
						rutor_nosd			=rutor_nosd,
	                    soap4me_login		=soap4me_login,
	                    soap4me_password	=soap4me_password,
						soap4me_rss			=soap4me_rss,
	                    preffered_bitrate 	=preffered_bitrate,
	                    preffered_type 		=preffered_type,
	                    preffered_codec     =preffered_codec,
	                    torrent_player 		=torrent_player,
	                    storage_path		=storage_path,
	                    movies_save 		=movies_save,
	                    animation_save 		=animation_save,
	                    documentary_save 	=documentary_save,
	                    anime_save 			=anime_save,
	                    tvshows_save 		=tvshows_save,
	                    animation_tvshows_save =animation_tvshows_save,
	                    torrent_path        =torrent_path,
						kp_googlecache		= kp_googlecache)

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

	start_time = time.time()
	start_play_max_time 	= int(_addon.getSetting(  'start_play_max_time'))	  # default 60 seconds
	search_seed_max_time = int(_addon.getSetting('search_seed_max_time'))  # default 15 seconds

	if episodeNumber != None:
		episodeNumber = int(episodeNumber)

	if settings == None:
		return play_torrent_variant.resultCancel

	if downloader:
		try:
			downloader.start(True)
		except:
			print_tb()

	torrent_info = None
	torrent_path = path

	from torrent2http import Error as TPError
	try:
		if settings.torrent_player == 'YATP':
			from yatpplayer import YATPPlayer
			player = YATPPlayer()
		elif settings.torrent_player == 'torrent2http':
			from torrent2httpplayer import Torrent2HTTPPlayer
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
					from tvshowapi import cutStr
					if cutName in unicode(cutStr(name)):
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
			player.updateCheckingProgress(info_dialog)

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

		from kodidb import KodiDB
		k_db = KodiDB(filename.replace(u'.nfo', u'.strm'), \
		              rel_path,
		              sys.argv[0] + sys.argv[2])
		k_db.PlayerPreProccessing()


		class OurPlayer(xbmc.Player):
			def __init__(self):
				xbmc.Player.__init__(self)
				self.show_overlay = False
				
				self.fs_video = xbmcgui.Window(12005)

				x = 20
				y = 120
				w = self.fs_video.getWidth()
				h = 100

				self.info_label = xbmcgui.ControlLabel(x, y, w, h, '', textColor='0xFF00EE00', font='font16')
				self.info_label_bg = xbmcgui.ControlLabel(x+2, y+2, w, h, '', textColor='0xAA000000', font='font16')

			def _show_progress(self):
				if settings.torrent_player == 'Ace Stream':
					return

				if not self.show_overlay:
					self.fs_video.addControls([self.info_label_bg, self.info_label])
					self.show_overlay = True

			def _hide_progress(self):
				if self.show_overlay:
					self.fs_video.removeControls([self.info_label_bg, self.info_label])
					self.show_overlay = False

			def UpdateProgress(self):
				#debug('UpdateProgress')
				if self.show_overlay:
					info = player.GetTorrentInfo()
					#debug(info)
					percent = float(info['downloaded']) * 100 / info['size'];
					#debug(percent)
					if percent >= 0:
						heading = u"{} МB из {} МB - {}%\n".format(info['downloaded'], info['size'], int(percent))
						if percent < 100:
							heading += u"Скорость загрузки: {} KB/сек\n".format(info['dl_speed'])
							heading += u"Сиды: {}    Пиры: {}".format(info['num_seeds'], info['num_peers'])
						#debug(heading)
						self.info_label.setLabel(heading)
						self.info_label_bg.setLabel(heading)
					
			def __del__(self):				self._hide_progress()
			def onPlayBackPaused(self):		self._show_progress()
			def onPlayBackResumed(self):	self._hide_progress()
			def onPlayBackEnded(self):		self._hide_progress()
			def onPlayBackStopped(self):	self._hide_progress()

		xbmc_player = OurPlayer()
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
			xbmc_player.UpdateProgress()

		debug('!!!!!!!!!!!!!!!!! END PLAYING !!!!!!!!!!!!!!!!!!!!!')

		xbmc.sleep(1000)

		k_db.PlayerPostProccessing()

		torrent_info = player.GetTorrentInfo()
		torrent_path = player.path
		info_hash = player.GetLastTorrentData()['info_hash']

		xbmc.executebuiltin('Container.Refresh')
		UpdateLibrary_path = filesystem.join(settings.base_path(), rel_path).encode('utf-8')
		debug(UpdateLibrary_path)
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video", "%s", "false")' % UpdateLibrary_path)

	except TPError as e:
		print_tb(e)
		return play_torrent_variant.resultTryNext

	finally:
		debug('FINALLY')
		player.close()

	if settings.run_script or settings.remove_files or settings.move_video or settings.copy_torrent:
		import afteractions
		afteractions.Runner(settings, params, playable_item, torrent_info, torrent_path, info_hash)

	return play_torrent_variant.resultOK


def get_path_or_url_and_episode(settings, params, torrent_source):
	tempPath = xbmc.translatePath('special://temp').decode('utf-8')
	
	from downloader import TorrentDownloader
	torr_downloader = TorrentDownloader(urllib.unquote(torrent_source), tempPath, settings)

	path = filesystem.join(settings.torrents_path(), torr_downloader.get_subdir_name(),
	                       torr_downloader.get_post_index() + '.torrent')
	if not filesystem.exists(path):
		if not torr_downloader.download():
			return None
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
	from nforeader import NFOReader

	info_dialog = xbmcgui.DialogProgress()
	info_dialog.create(settings.addon_name)

	tempPath = xbmc.translatePath('special://temp').decode('utf-8')
	base_path = settings.base_path().encode('utf-8')
	rel_path = urllib.unquote(params.get('path', ''))
	nfoFilename = urllib.unquote(params.get('nfo', ''))
	nfoFullPath = NFOReader.make_path(base_path, rel_path, nfoFilename)
	strmFilename = nfoFullPath.replace('.nfo', '.strm')
	nfoReader = NFOReader(nfoFullPath, tempPath) if filesystem.exists(nfoFullPath) else None

	debug(strmFilename.encode('utf-8'))
	
	from base import STRMWriterBase
	links_with_ranks = STRMWriterBase.get_links_with_ranks(strmFilename, settings, use_scrape_info=True)

	anidub_enable = _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable = _addon.getSetting('hdclub_enable') == 'true'
	bluebird_enable = _addon.getSetting('bluebird_enable') == 'true'
	nnmclub_enable = _addon.getSetting('nnmclub_enable') == 'true'
	rutor_enable = _addon.getSetting('rutor_enable') == 'true'
	soap4me_enable = _addon.getSetting('soap4me_enable') == 'true'

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
		if not bluebird_enable and 'bluebird.org' in v['link']:
			links_with_ranks.remove(v)
		if not nnmclub_enable and 'nnm-club.me' in v['link']:
			links_with_ranks.remove(v)
		if not rutor_enable and 'rutor.info' in v['link']:
			links_with_ranks.remove(v)
		if not soap4me_enable and 'soap4.me' in v['link']:
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
				info_dialog.update(0, settings.addon_name, 'Попытка #%d' % tryCount)
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
		if dialog.yesno(settings.addon_name, u'Источники категорий не созданы. Создать?'):
			if sources.create(settings):
				if dialog.yesno(settings.addon_name, restart_msg):
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


def dialog_action(action, settings, params=None):

	if action == dialog_action_case.generate:
		anidub_enable = _addon.getSetting('anidub_enable') == 'true'
		hdclub_enable = _addon.getSetting('hdclub_enable') == 'true'
		bluebird_enable = _addon.getSetting('bluebird_enable') == 'true'
		nnmclub_enable = _addon.getSetting('nnmclub_enable') == 'true'
		rutor_enable = _addon.getSetting('rutor_enable') == 'true'
		soap4me_enable = _addon.getSetting('soap4me_enable') == 'true'

		if not (anidub_enable or hdclub_enable or bluebird_enable or nnmclub_enable or rutor_enable or soap4me_enable):
			xbmcgui.Dialog().ok(_ADDON_NAME, u'Пожалуйста, заполните настройки', u'Ни одного сайта не выбрано')
			action = dialog_action_case.settings
		else:
			from service import start_generate
			# if check_sources(settings):
			start_generate()
			return True

	if action == dialog_action_case.sources:
		import sources

		dialog = xbmcgui.Dialog()
		if sources.create(settings):
			if dialog.yesno(settings.addon_name, restart_msg):
				from service import update_library_next_start

				update_library_next_start()
				xbmc.executebuiltin('Quit')

	if action == dialog_action_case.settings:
		save_nnmclub_login = settings.nnmclub_login
		save_nnmclub_password = settings.nnmclub_password
		_addon.openSettings()
		settings = load_settings()

		if save_nnmclub_login != settings.nnmclub_login or save_nnmclub_password != settings.nnmclub_password:
			from nnmclub import get_passkey
			passkey = get_passkey(settings=settings)
			_addon.setSetting('nnmclub_passkey', passkey)
			settings.nnmclub_passkey = passkey

	if action == dialog_action_case.search:
		if not 'keyword' in params:
			dlg = xbmcgui.Dialog()
			s = dlg.input(u'Введите поисковую строку')
			command = sys.argv[0] + sys.argv[2] + '&keyword=' + urllib.quote(s)
			xbmc.executebuiltin(b'Container.Update(\"%s\")' % command)
			debug('No keyword param. Return')
			return False

		s = urllib.unquote(params.get('keyword'))
		if s:
			from movieapi import MovieAPI

			debug('Keyword is: ' + s)
			show_list(MovieAPI.search(s.decode('utf-8')))

	if action == dialog_action_case.catalog:
		addon_handle = int(sys.argv[1])
		xbmcplugin.setContent(addon_handle, 'movies')

		listing = [

			('popular', u'Популярные'),
			('top_rated', u'Рейтинговые'),
			('popular_tv', u'Популярные сериалы'),
			('top_rated_tv', u'Рейтинговые сериалы')
		]

		if filesystem.exists('special://home/addons/plugin.video.shikimori.2'):
			listing.append(('anime', u'Аниме (Shikimori.org)' ), )

		for l in listing:
			li = xbmcgui.ListItem(l[1])
			li.setProperty("folder", "true")
			li.setProperty('IsPlayable', 'false')

			url = 'plugin://script.media.aggregator/?action=show_category&category=' + l[0]
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

		items = [(u'Смотрите также', 'Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % str(item.tmdb_id())),
				(u'Искать источники', 'RunPlugin("%s")' % (url + '&force=true') )]
		pathUnited = 'special://home/addons/plugin.video.united.search'
		pathUnited = xbmc.translatePath(pathUnited)

		if filesystem.exists(pathUnited.decode('utf-8')):
			items.append((u'United search', 'Container.Update("plugin://plugin.video.united.search/?action=search&keyword=%s")' % urllib.quote(info['title'].encode('utf-8'))))

		li.addContextMenuItems(items)

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
	xbmcplugin.endOfDirectory(addon_handle)


def force_library_update(settings, params):
	xbmc.executebuiltin('UpdateLibrary("video", "%s", "false")' % '/fake_path')
	xbmc.sleep(500)


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


def main_menu(menu_actions):
	
	indx = 0
	addon_handle = int(sys.argv[1])
	for menu in menu_items:
		li = xbmcgui.ListItem(menu)
		url = 'plugin://script.media.aggregator/?menu=' + menu_actions[indx]
		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=indx > dialog_action_case.settings)
		indx += 1
	
	xbmcplugin.endOfDirectory(addon_handle)

def action_add_media(params, settings):
	title = urllib.unquote_plus(params.get('title')).decode('utf-8')
	imdb = params.get('imdb')
	force = params.get('force') == 'true'
	
	if getSetting('role').decode('utf-8') == u'клиент' and params.get('norecursive'):
		force_library_update(settings, params)

	if force:
		from service import add_media
		add_media(title, imdb, settings)
		return
	
	import json
	found = None

	if imdb.startswith('sm') and title:
		req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]}, "id": "libTvShows"}
		result = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
		try:
			for r in result['result']['tvshows']:
				if r['originaltitle'] == title:
					found = 'tvshow'
					break
		except KeyError:
			debug('KeyError: Animes not found')
	
	if not found:
		req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]}, "id": "libMovies"}
		result = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
		try:
			for r in result['result']['movies']:
				if r['imdbnumber'] == imdb:
					found = 'movie'
					break
		except KeyError:
			debug('KeyError: Movies not found')
	
	if not found:
		req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]}, "id": "libTvShows"}
		result = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
		try:
			for r in result['result']['tvshows']:
				if r['imdbnumber'] == imdb:
					found = 'tvshow'
					break
		except KeyError:
			debug('KeyError: TVShows not found')
	
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
			add_media(title, imdb, settings)

def action_show_similar(params):
	from movieapi import MovieAPI
	listing = MovieAPI.show_similar(params.get('tmdb'))
	debug(listing)
	show_list(listing)

def action_show_category(params):
	from movieapi import MovieAPI
	if params.get('category') == 'popular':
		show_list(MovieAPI.popular())
	if params.get('category') == 'top_rated':
		show_list(MovieAPI.top_rated())
	if params.get('category') == 'popular_tv':
		show_list(MovieAPI.popular_tv())
	if params.get('category') == 'top_rated_tv':
		show_list(MovieAPI.top_rated_tv())
	if params.get('category') == 'anime':
		uri = 'plugin://plugin.video.shikimori.2/'
		xbmc.executebuiltin(b'Container.Update(\"%s\")' % uri)
		

def action_search_context(params):
	from movieapi import MovieAPI
	s = params.get('s')
	show_list(MovieAPI.search(s.decode('utf-8')))

def action_anidub_add_favorites(settings):
	debug('anidub-add-favorites')
	anidub_enable = _addon.getSetting('anidub_enable') == 'true'
	if anidub_enable:
		if settings.anime_save:
			from anidub import write_favorites
			debug('scan for anidub-add-favorites')
			write_favorites(settings.anime_tvshow_path(), settings)

def main():
	from service import create_mark_file
	create_mark_file()

	from dispatcher import dispatch
	dispatch()


if __name__ == '__main__':
	main()
