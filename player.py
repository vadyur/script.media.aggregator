# -*- coding: utf-8 -*-

import sys
import xbmcplugin, xbmcgui, xbmc, xbmcaddon
import anidub, hdclub, nnmclub, filesystem
import urllib, os, requests
import time
import operator
from settings import *
from nforeader import NFOReader
from yatpplayer import *
from torrent2httpplayer import *
from torrent2http import Error as TPError
from kodidb import *
from base import STRMWriterBase

# Определяем параметры плагина
_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)
_addon_path =   _addon.getAddonInfo('path').decode('utf-8')

def get_params():
	param=[]
	
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]

	#print param
	return param
	
def load_settings():
	base_path 			= _addon.getSetting('base_path').decode('utf-8')
	
	movies_path			= _addon.getSetting('movies_path').decode('utf-8')
	animation_path		= _addon.getSetting('animation_path').decode('utf-8')
	documentary_path	= _addon.getSetting('documentary_path').decode('utf-8')
	anime_path			= _addon.getSetting('anime_path').decode('utf-8')
	
	hdclub_passkey		= _addon.getSetting('hdclub_passkey')
	anidub_login		= _addon.getSetting('anidub_login')
	anidub_password		= _addon.getSetting('anidub_password')
	
	nnmclub_pages		= int(_addon.getSetting('nnmclub_pages'))
	nnmclub_login		= _addon.getSetting('nnmclub_login')
	nnmclub_password	= _addon.getSetting('nnmclub_password')
	
	preffered_bitrate 	= int(_addon.getSetting('preffered_bitrate'))
	preffered_type 		= _addon.getSetting('preffered_type')
	
	torrent_player 		= _addon.getSetting('torrent_player')
	storage_path		= _addon.getSetting('storage_path')
	
	
	settings 			= Settings(	base_path, 
									movies_path			= movies_path,
									animation_path		= animation_path,
									documentary_path	= documentary_path,
									anime_path			= anime_path,
									hdclub_passkey 		= hdclub_passkey, 
									anidub_login 		= anidub_login, 
									anidub_password 	= anidub_password, 
									nnmclub_pages 		= nnmclub_pages,
									nnmclub_login 		= nnmclub_login,
									nnmclub_password 	= nnmclub_password,
									preffered_bitrate 	= preffered_bitrate,
									preffered_type 		= preffered_type,
									torrent_player 		= torrent_player,
									storage_path		= storage_path)
	#print settings
	return settings
	
def play_torrent_variant(path, info_dialog, episodeNumber, nfoReader, settings, params):
	
	play_torrent_variant.resultOK 		= 'OK'
	play_torrent_variant.resultCancel 	= 'Cancel'
	play_torrent_variant.resultTryNext	= 'TryNext'
	
	start_time = time.time()
	start_play_max_time 	= 60	# 60 seconds
	search_seed_max_time	= 15	# 15 seconds
	
	if episodeNumber != None:
		episodeNumber = int(episodeNumber)

	if settings == None:
		return play_torrent_variant.resultCancel

	try:
		if settings.torrent_player == 'YATP':
			player = YATPPlayer()
		elif settings.torrent_player == 'torrent2http':
			player = Torrent2HTTPPlayer(settings)
			
		player.AddTorrent(path)

		added = False
		for i in range(start_play_max_time):
			if player.CheckTorrentAdded():
				added = True
				break
				
			if xbmc.abortRequested:
				return play_torrent_variant.resultCancel
				
			info_dialog.update(i, u'Проверяем файлы', ' ', ' ')

			xbmc.sleep(1000)
			
		if not added:
			print 'Torrent not added'
			return play_torrent_variant.resultTryNext
			
		files = player.GetLastTorrentData()['files']
		print files

		if episodeNumber != None:
			files.sort(key=operator.itemgetter('name'))		
		else:
			files.sort(key=operator.itemgetter('size'), reverse=True)
		print 'sorted_files:'
		print files
		
		
		if episodeNumber == None:
			index = 0
			playable_item = files[0]
		else:
			playable_item = files[episodeNumber]
			index = playable_item.get('index')
			
		print playable_item
			
			
		player.StartBufferFile(index)
		
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
						print 'Seeds not found'
						return play_torrent_variant.resultTryNext
				
			xbmc.sleep(1000)
			
		canceled = info_dialog.iscanceled()
		info_dialog.update(0)
		info_dialog.close()
		if canceled:
			return play_torrent_variant.resultCancel
		
		playable_url 	= player.GetStreamURL(playable_item)
		print playable_url
	
		handle = int(sys.argv[1])
		if nfoReader != None:
			list_item = nfoReader.make_list_item(playable_url)
		else:
			list_item = xbmcgui.ListItem(path=playable_url)
			
		rel_path = urllib.unquote(params['path']).decode('utf-8')
		filename = urllib.unquote(params['nfo']).decode('utf-8')
		
		k_db = KodiDB(	filename.replace(u'.nfo', u'.strm'), \
						rel_path,
						sys.argv[0] + sys.argv[2])
		k_db.PlayerPreProccessing()
			
		xbmc_player = xbmc.Player()
		xbmcplugin.setResolvedUrl(handle, True, list_item)
	
		while not xbmc_player.isPlaying():
			xbmc.sleep(300)
			
		print '!!!!!!!!!!!!!!!!! Start PLAYING !!!!!!!!!!!!!!!!!!!!!'
		
		if k_db.timeOffset != 0:
			print "Seek to time: " + str(k_db.timeOffset)
			xbmc.sleep(2000)
			xbmc_player.seekTime(int(k_db.timeOffset))
		
		# Wait until playing finished or abort requested
		while not xbmc.abortRequested and xbmc_player.isPlaying():
			xbmc.sleep(1000)
			
		print '!!!!!!!!!!!!!!!!! END PLAYING !!!!!!!!!!!!!!!!!!!!!'
		
		xbmc.sleep(1000)
		k_db.PlayerPostProccessing()
	
	except TPError as e:
		print e
		return play_torrent_variant.resultTryNext
		
	finally:
		player.close()

	return play_torrent_variant.resultOK
	
def get_path_or_url_and_episode(settings, params, torrent_source):
	tempPath = xbmc.translatePath('special://temp').decode('utf-8')
	if 'anidub' in torrent_source:
		path = filesystem.join(tempPath, u'temp.anidub.media-aggregator.torrent')
		print path
		if anidub.download_torrent(torrent_source, path, settings):
			return { 'path_or_url': path, 'episode': params.get('episodeNumber', None) }
	elif 'hdclub' in torrent_source:
		url = urllib.unquote(torrent_source).replace('details.php', 'download.php')
		if not 'passkey' in url:
			url += '&passkey=' + _addon.getSetting('hdclub_passkey')
		
		return { 'path_or_url': url, 'episode': params.get('episodeNumber', None) }
	elif 'nnm-club' in torrent_source:
		path = filesystem.join(tempPath, u'temp.nnm-club.media-aggregator.torrent')
		if settings.nnmclub_login != '' and settings.nnmclub_password != '' and nnmclub.download_torrent(torrent_source, path, settings):
			print 'Download torrent %s' % path
			return { 'path_or_url': path, 'episode': params.get('episodeNumber', None) }
		else:
			url = nnmclub.get_magnet_link(urllib.unquote(torrent_source))
			print 'Download magnet %s' % url
			return { 'path_or_url': url, 'episode': params.get('episodeNumber', None) }
	else:
		url = urllib.unquote(torrent_source)
		return { 'path_or_url': url, 'episode': params.get('episodeNumber', None) }
		
	return None
	
def play_torrent(path, episodeNumber, settings, params):
	info_dialog = xbmcgui.DialogProgress()
	info_dialog.create('Media Aggregator')
	
	tempPath 		= xbmc.translatePath('special://temp').decode('utf-8')
	base_path 		= settings.base_path().encode('utf-8')
	rel_path 		= urllib.unquote(params.get('path', ''))
	nfoFilename 	= urllib.unquote(params.get('nfo', ''))
	nfoFullPath 	= NFOReader.make_path(base_path, rel_path, nfoFilename)
	strmFilename 	= nfoFullPath.replace('.nfo', '.strm')
	nfoReader 		= NFOReader(nfoFullPath, tempPath) if filesystem.exists(nfoFullPath) else None

	if play_torrent_variant(path, info_dialog, episodeNumber, nfoReader, settings, params) == play_torrent_variant.resultTryNext:
		print strmFilename.encode('utf-8')
		links_with_ranks = STRMWriterBase.get_links_with_ranks(strmFilename)
		tryCount = 1
		for variant in links_with_ranks:
			tryCount += 1
			
			info_dialog.update(0, 'Media Aggregator', 'Попытка #%d' % tryCount)
			print variant
			
			#print "variant['link']=" + variant['link']
			#print sys.argv[0] + sys.argv[2]
			if variant['link'] in sys.argv[0] + sys.argv[2]:
				print "variant skipped"
				tryCount -= 1
				continue

			torrent_source = variant['link']
			try:
				torrent_source = torrent_source.split('torrent=')[1].split('&')[0]
			except:
				continue
				
			path_or_url_and_episode = get_path_or_url_and_episode(settings, params, torrent_source)
			if path_or_url_and_episode is None:
				continue
			
			if play_torrent_variant(path_or_url_and_episode['path_or_url'], info_dialog, episodeNumber, nfoReader, settings, params) != play_torrent_variant.resultTryNext:
				break
		
			
	info_dialog.update(0, '', '')
	info_dialog.close()

	
def main():
	params 		= get_params()
	print params
	settings	= load_settings()
	#print settings
	
	xbmc.log(settings.base_path())
	if 'torrent' in params:
		path_or_url_and_episode = get_path_or_url_and_episode(settings, params, params['torrent'])
		if not path_or_url_and_episode is None:
			play_torrent(path_or_url_and_episode['path_or_url'], path_or_url_and_episode['episode'], settings = settings, params = params)
	else:
		while True:
			dialog = xbmcgui.Dialog()
			rep = dialog.select(u'Выберите опцию:', [	u'Генерировать .strm и .nfo файлы',
														u'-НАСТРОЙКИ',
#														u'-ТЕСТ',
														u'Выход'])
			if rep == 0:
				anidub_enable		= _addon.getSetting('anidub_enable') == 'true'
				hdclub_enable		= _addon.getSetting('hdclub_enable') == 'true'
				nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'
				
				if anidub_enable:
					anidub.run(settings)
				if hdclub_enable:
					hdclub.run(settings)
				if nnmclub_enable:
					nnmclub.run(settings)
				if not (anidub_enable or hdclub_enable or nnmclub_enable):
					xbmcgui.Dialog().ok(_ADDON_NAME, u'Пожалуйста, заполните настройки', u'Ни одного сайта не выбрано')
					rep = 1
				else:
					xbmc.executebuiltin('UpdateLibrary("video")')
					
			if rep == 1:
				_addon.openSettings()
				settings = load_settings()
			'''				
			if rep == 2:
				adv_s = AdvancedSettingsReader()
				print adv_s['type']
				return
			'''				
			if rep > 1 or rep < 0:
				break
		

if __name__ == '__main__':
    main()
