# -*- coding: utf-8 -*-

# TorrServerPlayer

import requests, urllib
from base import TorrentPlayer

class TorrServerPlayer(TorrentPlayer):

	def _log(self, s):
		from log import debug
		debug('TorrServerPlayer: ' + str(s))

	def __init__(self, settings):
		self.engine = None
		self.file_id = None
		self.settings = settings

		TorrentPlayer.__init__(self)

	def close(self):
		pass

	def StartBufferFile(self, fileIndex):
		self._AddTorrent(self.path)
		self.engine.start(fileIndex)
		self.file_id = fileIndex

	def GetBufferingProgress(self):
		if self.engine:
			return self.engine.buffer_progress()

		return 0

	def CheckBufferComplete(self):
		if self.engine:
			prc = self.engine.buffer_progress()

			self._log('CheckBufferComplete - {}'.format(prc))

			if prc >= 100:
				return True
		return False

	def CheckTorrentAdded(self):
		if self.engine:
			self._log('CheckTorrentAdded - engine running')
			if self.engine.hash is None:
				self._log('CheckTorrentAdded - hash is None')
				return False
			return True
		else:
			self._log('CheckTorrentAdded - engine down')
			return TorrentPlayer.CheckTorrentAdded(self)
		
		return False

	def GetStreamURL(self, playable_item):
		self._log('GetStreamURL')
		index = playable_item.get('index')
		return self.engine.play_url(index)

	def _AddTorrent(self, path):
		import filesystem
		with filesystem.fopen(path, 'r') as f:
			import torrserve_stream
			from log import debug
			self.engine = torrserve_stream.Engine(data=f.read(), log=debug)
		
	def updateCheckingProgress(self, progressBar):
		pass

	def updateDialogInfo(self, progress, progressBar):

		ti = self.GetTorrentInfo()
		if ti:
			dialogText = u'Загружено: {} MB / {} MB'.format(ti['downloaded'], ti['size'])
			peersText = u' [{}: {}; {}: {}]'.format(u'Сидов', ti['num_seeds'], u'Пиров', ti['num_peers'])
			speedsText = u'{}: {} Mbit/s; {}: {} Mbit/s'.format(
				u'Загрузка', ti['dl_speed'] / 1024 * 8,
				u'Отдача', ti['ul_speed'] / 1024 * 8)
			progressBar.update(progress, dialogText + '          ' + peersText, speedsText)
		
	def GetTorrentInfo(self):
		st = self.engine.stat()

		try:
			return { 	'downloaded' : 	int(st['LoadedSize'] / 1024 / 1024),
						'size' : 		int(st['FileStats'][self.file_id]['Length'] / 1024 / 1024),
						'dl_speed' : 	int(st['DownloadSpeed']),
						'ul_speed' :	int(st['UploadSpeed']),
						'num_seeds' :	st['ConnectedSeeders'], 
						'num_peers' :	st['ActivePeers']
					}
		except:
			pass
			
		return None