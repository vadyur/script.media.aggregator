import requests, urllib
from base import TorrentPlayer

class YATPPlayer(TorrentPlayer):
	
	def close(self):
		pass
	
	def AddTorrent(self, path):
		'''
		Send a torrent to YATP usign add_torrent method. YATP accepts local and remote (http/https) 
		paths to .torrent files and magnet links. Warning: paths on networked filesystems (smb/nfs) are not supported!
		'''
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "add_torrent", "params": {'torrent': path}})
		print r.json()
		
	def CheckTorrentAdded(self):
		'''
		Periodically check if the torrent has been added to YATP using check_torrent_added method. 
		Usually, .torrent files are added almost instantaneously, but processing magnet links takes some time.
		'''
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "check_torrent_added"})
		print r.json()
		try:
			if r.json()['result']:
				return True
		except:
			pass

		return False
		
	def GetLastTorrentData(self):
		'''
		return { 'info_hash': str, 'files': [ {'index': int, 'name': str, 'size': long} ] }
		'''
		
		'''
		As soon as check_torrent_added returns true, get added torrent data using get_last_added_torrent method. 
		This method will return a JSON object containing a torrent`s info-hash as a string (technically, this is 
		an info-hash hexdigest) and the list of files in the torrent along with their sizes. The info-hash is used 
		as a primary torrent ID for other JSON-RPC methods.
		'''
		files = []
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "get_last_added_torrent"})
		torr_data = r.json()['result']
		print torr_data
		
		info_hash = torr_data['info_hash']
		
		index = 0
		for file in torr_data['files']:
			if TorrentPlayer.is_playable(file[0]):
				files.append({'index': index, 'name': file[0], 'size': long(file[1])})
			index = index + 1
			
		return { 'info_hash': info_hash, 'files': files }
		
	def StartBufferFile(self, fileIndex):
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "buffer_file", "params": {"file_index": fileIndex}})
		
	def CheckBufferComplete(self):
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "check_buffering_complete"})
		print r.json()
		print 'check_buffering_complete'
		try:
			if r.json()['result']:
				return True
		except:
			pass
			
		return False
		
	def GetBufferingProgress(self):
		result = -1
		r = requests.post('http://localhost:8668/json-rpc', json={"method": "get_buffer_percent"})
		try:
			result = r.json()['result']
		except:
			pass
			
		print str(result) + '%'
		return result
		
	def updateDialogInfo(self, progress, progressBar):
		progressBar.update(progress)
		
	def GetStreamURL(self, playable_item):
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
		
		return playable_url
