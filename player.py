# -*- coding: utf-8 -*-

import sys
import xbmcplugin, xbmcgui, xbmc, xbmcaddon
import anidub, hdclub, nnmclub
import urllib, os, requests
import time
import operator
from settings import Settings
from nforeader import NFOReader

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
	base_path 			= _addon.getSetting('base_path')
	hdclub_passkey		= _addon.getSetting('hdclub_passkey')
	anidub_login		= _addon.getSetting('anidub_login')
	anidub_password		= _addon.getSetting('anidub_password')
	
	nnmclub_pages		= int(_addon.getSetting('nnmclub_pages'))
	nnmclub_login		= _addon.getSetting('nnmclub_login')
	nnmclub_password	= _addon.getSetting('nnmclub_password')
	
	settings 			= Settings(	base_path, 
									hdclub_passkey = hdclub_passkey, 
									anidub_login = anidub_login, 
									anidub_password = anidub_password, 
									nnmclub_pages = nnmclub_pages,
									nnmclub_login = nnmclub_login,
									nnmclub_password = nnmclub_password	)
	#print settings
	return settings
	
def is_playable(name):
	filename, file_extension = os.path.splitext(name)
	return file_extension in ['.mkv', '.mp4', '.ts', '.avi', '.m2ts', '.mov']
	
def play_torrent(path, episodeNumber = None, nfoReader = None):
	if episodeNumber != None:
		episodeNumber = int(episodeNumber)
		
	'''
	Send a torrent to YATP usign add_torrent method. YATP accepts local and remote (http/https) 
	paths to .torrent files and magnet links. Warning: paths on networked filesystems (smb/nfs) are not supported!
	'''
	r = requests.post('http://localhost:8668/json-rpc', json={"method": "add_torrent", "params": {'torrent': path}})
	print r.json()

	'''
	Periodically check if the torrent has been added to YATP using check_torrent_added method. 
	Usually, .torrent files are added almost instantaneously, but processing magnet links takes some time.
	'''
	added = False
	for i in range(20):
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "check_torrent_added"})
		print r.json()
		try:
			if r.json()['result']:
				added = True
				break
		except:
			pass
		time.sleep(1)
		
	if not added:
		print 'Torrent not added'
		return False
		
	'''
	As soon as check_torrent_added returns true, get added torrent data using get_last_added_torrent method. 
	This method will return a JSON object containing a torrent`s info-hash as a string (technically, this is 
	an info-hash hexdigest) and the list of files in the torrent along with their sizes. The info-hash is used 
	as a primary torrent ID for other JSON-RPC methods.
	'''
	files = []
	r = requests.post('http://localhost:8668/json-rpc', json={"method": "get_last_added_torrent"})
	#try:
	torr_data = r.json()['result']
	print torr_data
	#info_hash = torr_data['info_hash']
	
	index = 0
	for file in torr_data['files']:
		if is_playable(file[0]):
			files.append({'index': index, 'name': file[0], 'size': long(file[1])})
		index = index + 1
	#except:
	#	return
		
	print files

	if episodeNumber != None:
		files.sort(key=operator.itemgetter('name'))		
	else:
		files.sort(key=operator.itemgetter('size'), reverse=True)
	print 'sorted_files:'
	print files
	
	
	'''
	Select a videofile from the torrent one way or another and send its index to YATP using buffer_file method.
	'''
	
	if episodeNumber == None:
		index = 0
		playable_item = files[0]
	else:
		playable_item = files[episodeNumber]
		index = playable_item.get('index')
		
	print playable_item
		
		
	r = requests.post('http://localhost:8668/json-rpc', json={"method": "buffer_file", "params": {"file_index": index}})
	
	'''
	Check buffering status using check_buffering_complete method. You can also get buffering progress via 
	get_buffer_percent method to show some feedback to a plugin user.
	'''
	info_dialog = xbmcgui.DialogProgress()
	info_dialog.create('Media Aggregator: буфферизация')
	info_dialog.update(0)

	while not info_dialog.iscanceled():
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "check_buffering_complete"})
		print 'check_buffering_complete'
		try:
			if r.json()['result']:
				break
		except:
			pass
		
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "get_buffer_percent"})
		try:
			info_dialog.update(r.json()['result'])
		except:
			pass
		
		time.sleep(1)
		
	canceled = info_dialog.iscanceled()
	info_dialog.close()
	
	if canceled:
		return false
		
	
	'''
	As soon as check_buffering_complete returns true, construct a playable URL by combining a Kodi machine hostname 
	or IP, the YATP server port number (8668 by default), /stream sub-path, and a URL-quoted relative path to the 
	videofile obtained from get_last_added_torrent method, and then pass this URL for Kodi to play. For example, 
	if a relative path to a videofile is foo/bar baz.avi then the full playable URL will be:
		
		http://<Kodi hostname or IP>:8668/stream/foo/bar%20baz.avi
	'''
	playable_url 	= 'http://localhost:8668/stream/'
	file_path 		= playable_item['name'].replace('\\', '/').encode('utf-8')
	playable_url	+= urllib.quote(file_path)
	
	print playable_url
	
	handle = int(sys.argv[1])
	if nfoReader != None:
		list_item = nfoReader.make_list_item(playable_url)
	else:
		list_item = xbmcgui.ListItem(path=playable_url)
		
	xbmcplugin.setResolvedUrl(handle, True, list_item)
			
def main():			
	params 		= get_params()
	print params
	settings	= load_settings()
	
	xbmc.log(settings.base_path())

	if 'torrent' in params:
		reader = None
		if 'path' in params and 'nfo' in params:
			base_path = settings.base_path().encode('utf-8')
			rel_path = urllib.unquote(params['path'])
			filename = urllib.unquote(params['nfo'])
			reader = NFOReader(NFOReader.make_path(base_path, rel_path, filename), xbmc.translatePath('special://temp'))
		
		if 'anidub' in params['torrent']:
			path = os.path.join(xbmc.translatePath('special://temp'), 'temp.anidub.media-aggregator.torrent')
			print path
			if anidub.download_torrent(params['torrent'], path, settings):
				play_torrent(path, params.get('episodeNumber', None), nfoReader = reader)
		elif 'hdclub' in params['torrent']:
			url = urllib.unquote(params['torrent']).replace('details.php', 'download.php')
			if not 'passkey' in url:
				url += '&passkey=' + _addon.getSetting('hdclub_passkey')
			
			play_torrent(url, nfoReader = reader)
		elif 'nnm-club' in params['torrent']:
			path = os.path.join(xbmc.translatePath('special://temp'), 'temp.nnm-club.media-aggregator.torrent')
			if settings.nnmclub_login != '' and settings.nnmclub_password != '' and nnmclub.download_torrent(params['torrent'], path, settings):
				print 'Download torrent %s' % path
				play_torrent(path, nfoReader = reader)
			else:
				url = nnmclub.get_magnet_link(urllib.unquote(params['torrent']))
				print 'Download magnet %s' % url
				play_torrent(url, nfoReader = reader)
		else:
			url = urllib.unquote(params['torrent'])
			play_torrent(url, nfoReader = reader)
	else:
		while True:
			dialog = xbmcgui.Dialog()
			rep = dialog.select(u'Выберите опцию:', [	u'Генерировать .strm и .nfo файлы',
														u'-НАСТРОЙКИ',
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
				
			if rep > 1 or rep < 0:
				break
		

if __name__ == '__main__':
    main()
