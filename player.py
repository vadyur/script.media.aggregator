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

debug(_addondir)

from plugin import make_url

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

	movies_path				= getSetting('movies_path', 'Movies').decode('utf-8')
	animation_path			= getSetting('animation_path', 'Animation').decode('utf-8')
	documentary_path		= getSetting('documentary_path', 'Documentary').decode('utf-8')
	anime_path				= getSetting('anime_path', 'Anime').decode('utf-8')

	from settings import Settings
	settings = Settings(base_path,
						movies_path				= movies_path,
						animation_path			= animation_path,
						documentary_path		= documentary_path,
						anime_path				= anime_path
						)

	settings.hdclub_passkey			= getSetting('hdclub_passkey')

	settings.bluebird_login			= getSetting('bluebird_login')
	settings.bluebird_password		= getSetting('bluebird_password')
	settings.bluebird_nouhd			= getSetting('bluebird_nouhd')

	settings.anidub_login			= getSetting('anidub_login')
	settings.anidub_password		= getSetting('anidub_password')
	settings.anidub_rss				= getSetting('anidub_rss')
	settings.anidub_favorite		= getSetting('anidub_favorite')

	settings.nnmclub_pages			= 3
	settings.nnmclub_login			= getSetting('nnmclub_login')
	settings.nnmclub_password		= getSetting('nnmclub_password')
	settings.nnmclub_domain			= getSetting('nnmclub_domain')
	settings.nnmclub_use_ssl		= getSetting('nnmclub_use_ssl') == 'true'

	settings.rutor_domain			= getSetting('rutor_domain')
	settings.rutor_filter			= getSetting('rutor_filter')

	settings.soap4me_login			= getSetting('soap4me_login')
	settings.soap4me_password		= getSetting('soap4me_password')
	settings.soap4me_rss			= getSetting('soap4me_rss')

	settings.preffered_bitrate		= int(getSetting('preffered_bitrate'))
	settings.preffered_type			= getSetting('preffered_type')
	settings.preffered_codec		= getSetting('preffered_codec')

	settings.torrent_player			= getSetting('torrent_player')
	settings.storage_path			= getSetting('storage_path')

	settings.movies_save			= getSetting('movies_save') == 'true'
	settings.animation_save			= getSetting('animation_save') == 'true'
	settings.documentary_save		= getSetting('documentary_save') == 'true'
	settings.anime_save				= getSetting('anime_save') == 'true'
	settings.tvshows_save			= getSetting('tvshows_save') == 'true'
	settings.animation_tvshows_save = getSetting('animation_tvshows_save') == 'true'

	settings.torrent_path			= getSetting('torrent_path')

	settings.rutor_nosd				= getSetting('rutor_nosd') == 'true'
	settings.addon_data_path		= _addondir
	if getSetting('data_path'):
		settings.addon_data_path	= getSetting('data_path')

	settings.run_script				= getSetting('run_script') == 'true'
	settings.script_params			= getSetting('script_params').decode('utf-8')

	settings.move_video				= getSetting('action_files').decode('utf-8') == u'переместить'
	settings.remove_files			= getSetting('action_files').decode('utf-8') == u'удалить'
	settings.copy_video_path		= getSetting('copy_video_path').decode('utf-8')

	settings.copy_torrent			= getSetting('copy_torrent') == 'true'
	settings.copy_torrent_path		= getSetting('copy_torrent_path').decode('utf-8')

	settings.use_kinopoisk			= getSetting('use_kinopoisk')	== 'true'
	settings.use_worldart			= getSetting('use_worldart')	== 'true'
	settings.kp_googlecache			= getSetting('kp_googlecache')	== 'true'
	settings.kp_usezaborona			= getSetting('kp_usezaborona')	== 'true'

	settings.show_sources			= getSetting('show_sources')	== 'true'

	settings.kinohd_enable			= getSetting('kinohd_enable')	== 'true'
	settings.kinohd_4k				= getSetting('kinohd_4k')		== 'true'
	settings.kinohd_1080p			= getSetting('kinohd_1080p')	== 'true'
	settings.kinohd_720p			= getSetting('kinohd_720p')		== 'true'
	settings.kinohd_3d				= getSetting('kinohd_3d')		== 'true'
	settings.kinohd_serial			= getSetting('kinohd_serial')	== 'true'

	return settings


def play_torrent_variant(path, info_dialog, episodeNumber, nfoReader, settings, params, downloader):
	import filecmp

	def _debug(msg):
		debug(u'play_torrent_variant: {}'.format(msg) )

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
		elif settings.torrent_player == 'Elementum':
			import elementumplayer
			player = elementumplayer.ElementumPlayer()


		_debug('------------ Open torrent: ' + path)
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
				#if not filecmp.cmp(path, downloader.get_filename()):
				if downloader.info_hash() and downloader.info_hash() != player.info_hash:
					downloader.move_file_to(path)
					_debug('play_torrent_variant.resultTryAgain')
					return play_torrent_variant.resultTryAgain
				else:
					_debug('Torrents are equal')
					downloader = None

			xbmc.sleep(1000)

		if not added:
			_debug('Torrent not added')
			return play_torrent_variant.resultTryNext

		files = player.GetLastTorrentData()['files']
		_debug(files)

		if 'cutName' not in params:
			if 'index' not in params:
				if episodeNumber is not None:
					files.sort(key=operator.itemgetter('name'))
				else:
					files.sort(key=operator.itemgetter('size'), reverse=True)
				_debug('sorted_files:')
				_debug(files)

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
					#if not filecmp.cmp(path, downloader.get_filename()):
					if downloader.info_hash() and downloader.info_hash() != player.info_hash:
						downloader.move_file_to(path)
						print 'play_torrent_variant.resultTryAgain'
						return play_torrent_variant.resultTryAgain
				xbmc.sleep(1000)

		_debug(playable_item)

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
						_debug('Seeds not found')
						return play_torrent_variant.resultTryNext

			if downloader and downloader.is_finished():
				#if not filecmp.cmp(path, downloader.get_filename()):
				if downloader.info_hash() and downloader.info_hash() != player.info_hash:
					downloader.move_file_to(path)
					_debug('play_torrent_variant.resultTryAgain')
					return play_torrent_variant.resultTryAgain
				else:
					_debug('Torrents are equal')
					downloader = None

			xbmc.sleep(1000)

		canceled = info_dialog.iscanceled()
		info_dialog.update(0)
		info_dialog.close()
		if canceled:
			return play_torrent_variant.resultCancel

		playable_url = player.GetStreamURL(playable_item)
		_debug(playable_url)

		handle = int(sys.argv[1])
		if nfoReader != None:
			list_item = nfoReader.make_list_item(playable_url)
		else:
			list_item = xbmcgui.ListItem(path=playable_url)

		_debug('ListItem created')

		rel_path = urllib.unquote(params['path']).decode('utf-8')
		filename = urllib.unquote(params['nfo']).decode('utf-8')

		from kodidb import KodiDB
		k_db = KodiDB(filename.replace(u'.nfo', u'.strm'), \
		              rel_path,
		              sys.argv[0] + sys.argv[2])
		k_db.PlayerPreProccessing()

		_debug('VideoDB PreProccessing: OK')

		class OurPlayer(xbmc.Player):
			def __init__(self):
				xbmc.Player.__init__(self)
				self.show_overlay = False
				
				self.fs_video = xbmcgui.Window(12005)

				x = 20
				y = int(getSetting('dnl_progress_offset', 120))
				w = self.fs_video.getWidth()
				h = 100

				self.info_label = xbmcgui.ControlLabel(x, y, w, h, '', textColor='0xFF00EE00', font='font16')
				self.info_label_bg = xbmcgui.ControlLabel(x+2, y+2, w, h, '', textColor='0xAA000000', font='font16')

			def _show_progress(self):
				if settings.torrent_player == 'Ace Stream':
					return

				if settings.torrent_player == 'Elementum':
					return

				if getSetting('show_dnl_progress', 'true') != 'true':
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
						heading = u"{} МB из {} МB - {}".format(info['downloaded'], info['size'], int(percent)) + r'%' + '\n'
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

		_debug('OurPlayer creaded')

		xbmcplugin.setResolvedUrl(handle, True, list_item)

		_debug('setResolvedUrl')

		while not xbmc_player.isPlaying():
			xbmc.sleep(300)

		_debug('!!!!!!!!!!!!!!!!! Start PLAYING !!!!!!!!!!!!!!!!!!!!!')

		if k_db.timeOffset != 0:
			_debug("Seek to time: " + str(k_db.timeOffset))
			xbmc.sleep(2000)
			xbmc_player.seekTime(int(k_db.timeOffset))

		# Wait until playing finished or abort requested
		while not xbmc.abortRequested and xbmc_player.isPlaying():
			player.loop()
			xbmc.sleep(1000)
			xbmc_player.UpdateProgress()

		_debug('!!!!!!!!!!!!!!!!! END PLAYING !!!!!!!!!!!!!!!!!!!!!')

		xbmc.sleep(1000)

		k_db.PlayerPostProccessing()

		torrent_info = player.GetTorrentInfo()
		torrent_path = player.path
		info_hash = player.GetLastTorrentData()['info_hash']

		xbmc.executebuiltin('Container.Refresh')
		UpdateLibrary_path = filesystem.join(settings.base_path(), rel_path).encode('utf-8')
		_debug(UpdateLibrary_path)
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video", "%s", "false")' % UpdateLibrary_path)

	except TPError as e:
		_debug(e)
		print_tb()
		return play_torrent_variant.resultTryNext

	except BaseException as e:
		_debug(e)
		print_tb()
		return play_torrent_variant.resultTryNext

	finally:
		_debug('FINALLY')
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

	debug(strmFilename)
	
	from base import STRMWriterBase
	links_with_ranks = STRMWriterBase.get_links_with_ranks(strmFilename, settings, use_scrape_info=True)

	anidub_enable = _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable = False
	bluebird_enable = _addon.getSetting('bluebird_enable') == 'true'
	nnmclub_enable = _addon.getSetting('nnmclub_enable') == 'true'
	rutor_enable = _addon.getSetting('rutor_enable') == 'true'
	soap4me_enable = _addon.getSetting('soap4me_enable') == 'true'
	kinohd_enable = _addon.getSetting('kinohd_enable') == 'true'

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
		if not kinohd_enable and 'kinohd' in v['link']:
			links_with_ranks.remove(v)


	debug('links_with_ranks: ' + str(links_with_ranks))

	play_torrent_variant_result = None
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

			torr_params = params.copy()

			try:
				import urlparse
				dct = urlparse.parse_qs(variant['link'])
				torr_params['index'] = dct['index'][0]
			except:
				pass

			play_torrent_variant_result = play_torrent_variant(path_or_url_and_episode['path_or_url'], info_dialog,
			                                                   episodeNumber, nfoReader, settings, torr_params, downloader)
			if play_torrent_variant_result == play_torrent_variant.resultTryAgain:
				play_torrent_variant_result = play_torrent_variant(path_or_url_and_episode['path_or_url'], info_dialog,
				                                                   episodeNumber, nfoReader, settings, torr_params, None)

			if play_torrent_variant_result != play_torrent_variant.resultTryNext:
				break

	info_dialog.update(0, '', '')
	info_dialog.close()

	try:
		if play_torrent_variant_result == play_torrent_variant.resultTryNext and not onlythis:
			# Open in torrenter
			openInTorrenter(nfoReader)
	except:
		pass


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
	medialibrary = 5
	exit = 6


def dialog_action(action, settings, params=None):

	if action == dialog_action_case.generate:
		anidub_enable = _addon.getSetting('anidub_enable') == 'true'
		hdclub_enable = False
		bluebird_enable = _addon.getSetting('bluebird_enable') == 'true'
		nnmclub_enable = _addon.getSetting('nnmclub_enable') == 'true'
		rutor_enable = _addon.getSetting('rutor_enable') == 'true'
		soap4me_enable = _addon.getSetting('soap4me_enable') == 'true'
		kinohd_enable = _addon.getSetting('kinohd_enable') == 'true'

		if not (anidub_enable or hdclub_enable or bluebird_enable or nnmclub_enable or rutor_enable or soap4me_enable or kinohd_enable):
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

		"""
		if save_nnmclub_login != settings.nnmclub_login or save_nnmclub_password != settings.nnmclub_password:
			from nnmclub import get_passkey
			passkey = get_passkey(settings=settings)
			_addon.setSetting('nnmclub_passkey', passkey)
			settings.nnmclub_passkey = passkey
		"""

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
			from movieapi import TMDB_API

			debug('Keyword is: ' + s)
			show_list(TMDB_API.search(s.decode('utf-8')))

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

	if action == dialog_action_case.medialibrary:
		addon_handle = int(sys.argv[1])
		xbmcplugin.setContent(addon_handle, 'movies')

		listing = [

			('anime_top', u'Аниме: популярное'),
			('anime_recomended', u'Аниме: текущее'),
			('anime_last', u'Аниме: последнее'),

			('animation_top', u'Мультфильмы: популярное'),
			('animation_recomended', u'Мультфильмы: текущее'),
			('animation_last', u'Мультфильмы: последнее'),

			('animtv_top', u'Мультсериалы: популярное'),
			('animtv_recomended', u'Мультсериалы: текущее'),
			('animtv_last', u'Мультсериалы: последнее'),

			('documentary_top', u'Документальные фильмы: популярное'),
			('documentary_recomended', u'Документальные фильмы: текущее'),
			('documentary_last', u'Документальные фильмы: последнее'),

			('movie_top', u'Художественные фильмы: популярное'),
			('movie_recomended', u'Художественные фильмы: текущее'),
			('movie_last', u'Художественные фильмы: последнее'),

			('tvshow_top', u'Сериалы: популярное'),
			('tvshow_recomended', u'Сериалы: текущее'),
			('tvshow_last', u'Сериалы: последнее'),

		]

		for l in listing:
			li = xbmcgui.ListItem(l[1])
			li.setProperty("folder", "true")
			li.setProperty('IsPlayable', 'false')

			url = 'plugin://script.media.aggregator/?action=show_library&category=' + l[0]
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

		xbmcplugin.endOfDirectory(addon_handle)


	if action > dialog_action_case.settings or action < dialog_action_case.generate:
		return True

	return False

def next_item(total_pages):
	'''	returns True if current listing is next page
		else return False
	'''
	if not total_pages:
		return False

	from plugin import get_params
	params = get_params()
	if params:
		page = int(params.get('page', 1))
		if page < total_pages:
			params['page'] = page + 1
			url = make_url(params)

			addon_handle = int(sys.argv[1])
			li = xbmcgui.ListItem(u'[Далее]')
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
		return page > 1
	else:
		return False


def show_list(listing):
	addon_handle = int(sys.argv[1])
	xbmcplugin.setContent(addon_handle, 'movies')
	for item in listing:
		info = item.get_info()
		li = xbmcgui.ListItem(info['title'])
		li.setInfo('video', info)
		li.setArt(item.get_art())

		url_search = make_url(
			{'action': 'add_media',
			 'title': info['title'].encode('utf-8'),
			 'imdb': item.imdb()})

		url_similar = make_url(
			{'action': 'show_similar',
			 'type': item.type,
			 'tmdb': item.tmdb_id()})

		items = [(u'Смотрите также', 'Container.Update("%s")' % url_similar),
				(u'Искать источники', 'RunPlugin("%s")' % (url_search + '&force=true') )]

		li.addContextMenuItems(items)

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_search, listitem=li)
	
	updateListing = next_item(listing.total_pages)
	xbmcplugin.endOfDirectory(addon_handle, updateListing=updateListing, cacheToDisc=True)


def force_library_update(settings, params):
	xbmc.executebuiltin('UpdateLibrary("video", "%s", "false")' % '/fake_path')
	xbmc.sleep(500)


menu_items = [u'Генерировать .strm и .nfo файлы',
				u'Создать источники',
				u'Настройки',
				u'Поиск',
				u'Каталог',
				u'Медиатека'
]

menu_actions = ['generate',
		        'sources',
				'settings',
				'search',
				'catalog',
				'medialibrary'
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
		#req = {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "year", "file", "imdbnumber"]}, "id": "libMovies"}
		#result = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
		from complex_requests import get_movies_by_imdb
		result = get_movies_by_imdb(imdb)
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
	from movieapi import TMDB_API
	page = params.get('page', 1)
	listing = TMDB_API.show_similar_t(page, params.get('tmdb'), params.get('type'))
	debug(listing)
	show_list(listing)

def action_show_category(params):
	page = params.get('page', 1)

	import vsdbg
	#vsdbg._bp()

	from movieapi import TMDB_API
	if params.get('category') == 'popular':
		show_list(TMDB_API.popular(page))
	if params.get('category') == 'top_rated':
		show_list(TMDB_API.top_rated(page))
	if params.get('category') == 'popular_tv':
		show_list(TMDB_API.popular_tv(page))
	if params.get('category') == 'top_rated_tv':
		show_list(TMDB_API.top_rated_tv(page))
	if params.get('category') == 'anime':
		uri = 'plugin://plugin.video.shikimori.2/'
		xbmc.executebuiltin(b'Container.Update(\"%s\")' % uri)

def action_show_library(params):
	addon_handle = int(sys.argv[1])

	def _get_cast(castData):
		listCast = []
		listCastAndRole = []
		for castmember in castData:
			listCast.append(castmember["name"])
			listCastAndRole.append((castmember["name"], castmember["role"]))
		return [listCast, listCastAndRole]


	def _get_first_item(item):
		if len(item) > 0:
			item = item[0]
		else:
			item = ""
		return item


	def _get_joined_items(item):
		if len(item) > 0:
			item = " / ".join(item)
		else:
			item = ""
		return item


	class query:
		fields = ["title", "originaltitle", "year", "file", "imdbnumber", 'cast', 
					'country', 'genre', 'plot', 'plotoutline', 'tagline', 'rating',
					'votes', 'mpaa', 'trailer', 'playcount',
					"resume", "art",
				]
		content = 'movies'

		def method(self):
			return "VideoLibrary.GetMovies"


		def skip(self, item, type='movie', imdbs = []):

			if item['imdbnumber'] and item['imdbnumber'] in imdbs:
				return True

			if item['imdbnumber']:
				imdbs.append(item['imdbnumber'])

			if type == 'movie' and 'episode' in item['file']:
				return True

			if 'anime' in self.category:
				return 'Anime' not in item['file']

			if 'animation' in self.category:
				return 'Animation' not in item['file']

			if 'movie' in self.category:
				return 'Movies' not in item['file']

			if 'documentary' in self.category:
				return 'Documentary' not in item['file']

			if 'tvshow' in self.category:
				if 'Animation' not in item['file']:
					return 'TVShows' not in item['file']

			if 'animtv' in self.category:
				return 'Animation TVShows' not in item['file']

			return True

		def full_listing(self):
			xbmcplugin.setContent(addon_handle, self.content)
			xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_NONE, "%R")

			self.listing()
			xbmcplugin.endOfDirectory(addon_handle)


		def listing(self):

			result = self.req()['result']
			plot_enable = True
	
			isFolder = False
			ll = result.get('movies', []) 
			if not ll:
				ll = result.get('files', [])
			if not ll:
				ll = result.get('tvshows', [])
				if ll:
					isFolder = True

			imdbs = []

			for movie in ll:
				if self.skip(movie):
					continue

				if "cast" in movie:
					cast = _get_cast(movie['cast'])
				else:
					cast = [None, None]

				full_title = u"{} ({})".format(movie['title'], movie['year']) if movie['year'] and self.content == 'movies' else movie['title']

				li = xbmcgui.ListItem(full_title)
				url = movie['file']
				li.setInfo(type="Video", infoLabels={
					"Title": full_title,
					"OriginalTitle": movie['originaltitle'],
					"Year": movie['year'],
					"Genre": _get_joined_items(movie.get('genre', "")),
					"Studio": _get_first_item(movie.get('studio', "")),
					"Country": _get_first_item(movie.get('country', "")),
					"Plot": movie['plot'],
					"PlotOutline": movie.get('plotoutline', ''),
					"Tagline": movie.get('tagline', ''),
					"Rating": str(float(movie['rating'])),
					"Votes": movie['votes'],
					"MPAA": movie['mpaa'],
					"Director": _get_joined_items(movie.get('director', "")),
					"Writer": _get_joined_items(movie.get('writer', "")),
					"Cast": cast[0],
					"CastAndRole": cast[1],
					"mediatype": "movie",
					"Trailer": movie.get('trailer', ''),
					"Playcount": movie['playcount']})
 
				if 'resume' in movie:	
					li.setProperty("resumetime", str(movie['resume']['position']))
					li.setProperty("totaltime", str(movie['resume']['total']))
				#li.setProperty("type", ADDON_LANGUAGE(list_type))
				
				if 'movieid' in movie:
					li.setProperty("dbid", str(movie['movieid']))
				li.setProperty("imdbnumber", str(movie['imdbnumber']))
				li.setProperty("fanart_image", movie['art'].get('fanart', ''))
				li.setArt(movie['art'])
				li.setThumbnailImage(movie['art'].get('poster', ''))
				li.setIconImage('DefaultVideoCover.png')

				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=isFolder)

		def req(self, sort=None, filter=None, limits=None):
			_r = {"jsonrpc": "2.0", "method": self.method(), "params": {"properties": self.fields}, "id": "53257"}

			if sort:
				_r['params']['sort'] = sort

			if filter:
				_r['params']['filter'] = filter

			if limits:
				_r['params']['limits'] = limits

			import xbmc, json
			jsn = json.loads(xbmc.executeJSONRPC(json.dumps(_r)))

			return jsn

		def req_ldp(self, type):
			import xbmc, json
			cmd = 'plugin://service.library.data.provider/?type=' + type
			jsn = json.loads(xbmc.executeJSONRPC(json.dumps(
					{"jsonrpc": "2.0", 
					"method": "Files.GetDirectory", "params": {"properties": self.fields, "directory": cmd, "media":"files"}, "id": "1"}
				)))
			return jsn

	class query_tv(query):
		def __init__(self):
			
			self.fields = ["title", "originaltitle", "year", "file", "imdbnumber", 'cast', 
					 'genre', 'plot', 'rating',
					'votes', 'mpaa', 'playcount',
					 "art",
				]
			self.content = 'tvshows'

		def method(self):
			return "VideoLibrary.GetTVShows"

		def listing(self):
			#xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_NONE, "%R")
			
			query.listing(self)


	class query_tv_ep(query_tv):
		def __init__(self):
			self.fields = ["title", "plot", "votes", "rating", "writer", "firstaired", "playcount", "runtime", "director",
							"productioncode", "season", "episode", "originaltitle", "showtitle", "cast", "streamdetails",
							"lastplayed", "fanart", "thumbnail", "file", "resume", "tvshowid", "dateadded", "uniqueid", "art",
							"specialsortseason", "specialsortepisode", "userrating", "seasonid", "ratings"]

			self.content = 'episodes'

		def method(self):
			return "VideoLibrary.GetEpisodes"

		def req_ldp(self, type):
			import xbmc, json
			cmd = 'plugin://service.library.data.provider/?type=' + type

			props = [ "imdbnumber", "title", "episode", "season", "firstaired", "plot", "showtitle", "rating", "mpaa", 
					'playcount', "cast", 'resume', "art"
					]

			jsn = json.loads(xbmc.executeJSONRPC(json.dumps(
					{"jsonrpc": "2.0", 
					"method": "Files.GetDirectory", 
					"params": {"properties": props, "directory": cmd, "media":"video"}, "id": "1"}
				)))


			return jsn


		def listing(self):

			xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_NONE, "%J")

			result = self.req()['result']
			plot_enable = True
	
			ll = result.get('episodes', []) 
			if not ll:
				ll = result.get('files', [])


			for episode in ll:
				if self.skip(episode, type='episode'):
					continue

				if "cast" in episode:
					cast = _get_cast(episode['cast'])
				else:
					cast = [None, None]

				nEpisode = "%.2d" % float(episode['episode'])
				nSeason = "%.2d" % float(episode['season'])
				fEpisode = "s%se%s" % (nSeason, nEpisode)

				full_title = u'{} - {}x{} {}'.format(episode['showtitle'], episode['episode'], episode['season'], episode['title'])
				li = xbmcgui.ListItem(full_title)
				url = episode['file']

				li.setInfo(type="Video", infoLabels={
					"Title": full_title,
					"Episode": episode['episode'],
					"Season": episode['season'],
					"Studio": _get_first_item(episode.get('studio', "")),
					"Premiered": episode['firstaired'],
					"Plot": episode['plot'],
					"TVshowTitle": episode['showtitle'],
					"Rating": str(float(episode['rating'])),
					"MPAA": episode['mpaa'],
					"Playcount": episode['playcount'],
					"Director": _get_joined_items(episode.get('director', "")),
					"Writer": _get_joined_items(episode.get('writer', "")),
					"Cast": cast[0],
					"CastAndRole": cast[1],
					"mediatype": "episode"})
				li.setProperty("episodeno", fEpisode)
				li.setProperty("resumetime", str(episode['resume']['position']))
				li.setProperty("totaltime", str(episode['resume']['total']))
				#li.setProperty("type", ADDON_LANGUAGE(list_type))
				li.setProperty("fanart_image", episode['art'].get('tvshow.fanart', ''))
				#li.setProperty("dbid", str(episode['episodeid']))
				li.setArt(episode['art'])
				li.setThumbnailImage(episode['art'].get('tvshow.poster', ''))
				li.setIconImage('DefaultTVShows.png')

				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)

	class recentmovies(query):
		items = ['animation_last', 'documentary_last', 'movie_last']

		def req(self):
			return self.req_ldp('recentmovies')

	class recenttvshows(query_tv):
		items = ['anime_last', 'tvshow_last', 'animtv_last']

		def req(self):
			return query_tv.req(self, 
									sort={ "order": "descending", "method": "dateadded", "ignorearticle": True },
									limits={ "start" : 0, "end": 250 })

	class recommendedmovies(query):
		items = ['animation_recomended', 'documentary_recomended', 'movie_recomended']

		def req(self):
			return self.req_ldp('recommendedmovies')

	class recommendedepisodes(query_tv_ep):
		items = ['anime_recomended', 'tvshow_recomended', 'animtv_recomended']

		def req(self):
			return self.req_ldp('recommendedepisodes')

	class topmovies(query):
		items = ['movie_top', 'documentary_top', 'animation_top']

		def req(self):
			return query.req(self, 
									sort={ "order": "descending", "method": "rating", "ignorearticle": True },
									limits={ "start" : 0, "end": 250 })

	class toptvshows(query_tv):
		items = ['anime_top', 'tvshow_top', 'animtv_top']
		def req(self):
			return query_tv.req(self, 
									sort={ "order": "descending", "method": "rating", "ignorearticle": True },
									limits={ "start" : 0, "end": 250 })

	ldp_query = {
		'recentmovies': recentmovies(),
		'recommendedmovies': recommendedmovies(),
		'recommendedepisodes': recommendedepisodes(),
		'topmovies': topmovies(),
		'toptvshows': toptvshows(),
		'recenttvshows': recenttvshows()
	}

	import vsdbg
	vsdbg._bp()

	for q, l in ldp_query.iteritems():
		if params.get('category') in l.items:
			l.category = params.get('category')
			l.full_listing()
		

def action_search_context(params):
	from movieapi import TMDB_API
	s = params.get('s')
	show_list(TMDB_API.search(s.decode('utf-8')))

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
	#import vsdbg
	#vsdbg._bp()
	main()
