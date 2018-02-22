from base import TorrentPlayer
import filesystem
import base64

from log import debug


class AcePlayer(TorrentPlayer):
	def __init__(self, settings):
		self.settings = settings
		from ASCore import TSengine
		self.engine = TSengine()
		del TSengine

		TorrentPlayer.__init__(self)

	def close(self):
		if self.engine != None:
			self.engine.end()
			self.engine = None

	def _AddTorrent(self, path):
		if filesystem.exists(path):
			with filesystem.fopen(path, 'rb') as tfile:
				content = tfile.read()

			try:
				self.status = self.engine.load_torrent(base64.b64encode(content), 'RAW')
			except KeyError:
				pass

				debug('AcePlayer: Torrent loaded')

	def StartBufferFile(self, fileIndex):
		self._AddTorrent(self.path)
		self.fileIndex = fileIndex

	def GetStreamURL(self, playable_item):
		file_path = playable_item['name'].replace('\\', '/').encode('utf-8')
		link = str(self.engine.get_link(int(self.fileIndex), file_path))
		debug('AcePlayer: GetStreamURL - ' + link)
		return  link

	def loop(self):
		self.engine.loop()
