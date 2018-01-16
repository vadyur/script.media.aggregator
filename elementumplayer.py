# elementumplayer

import requests, urllib
from base import TorrentPlayer

class ElementumPlayer(TorrentPlayer):

	def _log(self, s):
		from log import debug
		debug('ElementumPlayer: ' + str(s))

	def close(self):
		pass

	def StartBufferFile(self, fileIndex):
		self.fileIndex = fileIndex

	def GetStreamURL(self, playable_item):
		index = playable_item.get('index')
		result = 'http://localhost:65220/play?uri={}&index={}'.format(urllib.quote(self.magnet()), index)
		self._log('GetStreamURL return ' + result)
		return result

	def magnet(self):
		td = self.GetLastTorrentData()
		result = 'magnet:?xt=urn:btih:{}&tr={}'.format(td['info_hash'], urllib.quote(td['announce']))
		self._log('magnet return ' + result)
		return result
