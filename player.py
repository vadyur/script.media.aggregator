﻿# -*- coding: utf-8 -*-

import sys
import xbmcplugin, xbmcgui, xbmc, xbmcaddon
import anidub, hdclub
import urllib, os, requests
import time
import operator
from settings import Settings

# Определяем параметры плагина
_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)
_addon_id   =   int(sys.argv[1])
_addon_url  =   sys.argv[0]
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

	print param
    return param
	
def load_settings():
	base_path 			= _addon.getSetting('base_path')
	hdclub_passkey		= _addon.getSetting('hdclub_passkey')
	anidub_login		= _addon.getSetting('anidub_login')
	anidub_password		= _addon.getSetting('anidub_password')

	settings 			= Settings(base_path, hdclub_passkey = hdclub_passkey, anidub_login = anidub_login, anidub_password = anidub_password)
	print settings
	return settings
	
def is_played(item):
	return True
	
def play_torrent(path, episodeNumber = None):
	if episodeNumber != None:
		episodeNumber = int(episodeNumber)
		print 'play_torrent: %s (%d)' % (path, episodeNumber)
	else:
		print 'play_torrent: %s' % path

		
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
	for i in range(10):
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "check_torrent_added"})
		try:
			if r.json()['result']:
				break
		except:
			pass
		time.sleep(1)
		
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
	item = {'index': 0, 'name': '', 'size': ''}
	for file in torr_data['files']:
		item['index'] 	= index
		item['name'] 	= file[0]
		item['size']	= file[1]
		if is_played(item):
			files.append({'index': index, 'name': file[0], 'size': file[1]})
			print item
		index = index + 1
	#except:
	#	return
		
	print files

	if episodeNumber == None:
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
	while True:
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "check_buffering_complete"})
		print 'check_buffering_complete'
		try:
			if r.json()['result']:
				break
		except:
			pass
		time.sleep(1)
	
	'''
	As soon as check_buffering_complete returns true, construct a playable URL by combining a Kodi machine hostname 
	or IP, the YATP server port number (8668 by default), /stream sub-path, and a URL-quoted relative path to the 
	videofile obtained from get_last_added_torrent method, and then pass this URL for Kodi to play. For example, 
	if a relative path to a videofile is foo/bar baz.avi then the full playable URL will be:
		
		http://<Kodi hostname or IP>:8668/stream/foo/bar%20baz.avi
	'''
	playable_url 	= 'http://localhost:8668/stream/'
	file_path 		= playable_item['name'].replace('\\', '/').encode('utf-8')
	playable_url	+= file_path
	
	print playable_url
	
	handle = int(sys.argv[1])
	list_item = xbmcgui.ListItem(path=playable_url)
	xbmcplugin.setResolvedUrl(handle, True, list_item)
			

			
params 		= get_params()
settings	= load_settings()

if 'torrent' in params:
	if 'anidub' in params['torrent']:
		path = os.path.join(xbmc.translatePath('special://temp'), 'temp.torrent')
		print path
		if anidub.download_torrent(params['torrent'], path, settings):
			play_torrent(path, params.get('episodeNumber', None))
	elif 'hdclub' in params['torrent']:
		url = urllib.unquote(params['torrent']).replace('details.php', 'download.php')
		play_torrent(url)
	else:
		url = urllib.unquote(params['torrent'])
		play_torrent(url)
else:
	dialog = xbmcgui.Dialog()
	rep = dialog.select('Choose an Option:', [	'Read [COLOR ffff9900]RSS[/COLOR] lists and create .strm Files in',
												'-SETTINGS',
												'Exit'])
	if rep == 0:
		anidub.run(settings)
		hdclub.run(settings)
	if rep == 1:
		_addon.openSettings()
		settings = load_settings()
		

