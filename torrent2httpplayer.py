from torrent2http import State, Engine, MediaType, Encryption
#from contextlib import closing
from base import TorrentPlayer

import urlparse, urllib, time, filesystem, xbmc, xbmcaddon

def path2url(path):
    return urlparse.urljoin('file:', urllib.pathname2url(path))
	
_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)

dht_routers 		= ["router.bittorrent.com:6881","router.utorrent.com:6881"]
user_agent 			= 'uTorrent/2200(24683)'

def getSetting(settings_name):
	return _addon.getSetting(settings_name)

class Torrent2HTTPPlayer(TorrentPlayer):
	
	def debug(self, msg):
		try:
			print '[Torrent2HTTPPlayer] %s' % msg
		except:
			pass
			
	def debug_assignment(self, value, varname):
		try:
			self.debug('%s: %s' % (varname, str(value)))
		except:
			pass
		return value
		
	def __init__(self, settings):
		self.engine = None
		self.file_id = None
		self.settings = settings
		
		self.pre_buffer_bytes 	= self.debug_assignment(int(getSetting('pre_buffer_bytes'))*1024*1024, 'pre_buffer_bytes') 		
		
		self.debug('__init__')
		
	def close(self):
		if self.engine != None:
			self.engine.close()
			self.engine = None
			
		self.debug('close')
		
	def __exit__(self):
		self.debug('__exit__')
		self.close()
		
	def AddTorrent(self, path):
		if filesystem.exists(path):
			uri = path2url(path)
		else:
			uri = path
		self.debug('AddTorrent: ' + uri) 
		
		download_path = self.settings.storage_path
		if download_path == '':
			download_path = xbmc.translatePath('special://temp')
			
		self.debug('download_path: %s' % download_path)	
		
		encryption = self.debug_assignment( Encryption.ENABLED if getSetting('encryption') == 'true' else Encryption.DISABLED ,'encryption')
		upload_limit = self.debug_assignment( int(getSetting("upload_limit")) * 1024 if getSetting("upload_limit") != "" else 0 ,"upload_limit")
		download_limit = self.debug_assignment( int(getSetting("download_limit")) * 1024 if getSetting("download_limit") != "" else 0 ,"download_limit")

		if getSetting("connections_limit") not in ["",0,"0"]:
			connections_limit = self.debug_assignment( int(getSetting("connections_limit")), "connections_limit")
		else:
			connections_limit = None

		use_random_port = self.debug_assignment( True if getSetting('use_random_port') == 'true' else False, 'use_random_port')
		listen_port = self.debug_assignment( int(getSetting("listen_port")) if getSetting("listen_port") != "" else 6881, "listen_port")
		
		
		self.engine = Engine(uri=uri, download_path=download_path, user_agent=user_agent, encryption=encryption, \
							upload_kbps=upload_limit, download_kbps=download_limit, connections_limit=connections_limit, \
							keep_incomplete=False, keep_complete=True, dht_routers=dht_routers, use_random_port=use_random_port, listen_port=listen_port,\
							log_files_progress=True)
		self.engine.start(0)
		
	def CheckTorrentAdded(self):
		status = self.engine.status()		
		self.engine.check_torrent_error(status)
		
		self.debug('CheckTorrentAdded')
		
		if status.state == State.CHECKING_FILES:
			self.debug('State.CHECKING_FILES')
			return False
		
		return True
		
	def GetLastTorrentData(self):
		while True:
			time.sleep(0.2)
			
			# Get torrent files list, filtered by video file type only
			files = self.engine.list() #(media_types=[MediaType.VIDEO])
			# If torrent metadata is not loaded yet then continue
			if files is None:
				self.debug('files is None')
				continue
				
			self.debug('files len: ' + str(len(files)))
			
			# Torrent has no video files
			if not files or len(files) > 0:
				break
				
		info_hash = ''
		playable_items = []
		for item in files:
			if TorrentPlayer.is_playable(item.name):
				playable_items.append({'index': item.index, 'name': item.name, 'size': long(item.size)})
		
		return { 'info_hash': info_hash, 'files': playable_items }
		
	def StartBufferFile(self, fileIndex):
		if fileIndex != 0:
			self.engine.close()
			self.engine.start(fileIndex)
		#status = self.engine.file_status(fileIndex)
		self.file_id = fileIndex
		
		self.debug('StartBufferFile: %d' % fileIndex)
		
	def CheckBufferComplete(self):
		status = self.engine.status()
		self.debug('CheckBufferComplete: ' + str(status.state_str))
		if status.state == State.DOWNLOADING:
			# Wait until minimum pre_buffer_bytes downloaded before we resolve URL to XBMC
			f_status = self.engine.file_status(self.file_id)
			self.debug('f_status.download %d' % f_status.download)
			if f_status.download >= self.pre_buffer_bytes:
				return True

		return status.state in [State.FINISHED, State.SEEDING]

	def GetBufferingProgress(self):
		f_status = self.engine.file_status(self.file_id)
		
		try:
			progress = int(round(float(f_status.download) / self.pre_buffer_bytes, 2) * 100)
			self.debug('GetBufferingProgress: %d' % progress)
			if progress > 99: 
				progress = 99
		except:
			progress = 0
		
	
		return progress
		
	def GetStreamURL(self, playable_item):
		f_status = self.engine.file_status(self.file_id)
		
		self.debug('GetStreamURL: %s' % f_status.url)
		
		return f_status.url