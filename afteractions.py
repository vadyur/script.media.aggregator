import log
from log import debug


import os
import urllib

import filesystem

class Runner(object):
	def __init__(self, settings, params, playable_item, torrent_info, torrent_path):
		self.command = settings.script_params.split(u' ')
		self.settings = settings
		self.params = params
		self.torrent_info = torrent_info
		self.torrent_path = torrent_path
		self.playable_item = playable_item
		
		debug('-' * 30 + ' Runner ' + '-' * 30)
		debug('torrent: ' + self.torrent)
		debug('videofile: ' + self.videofile)
		debug('relativevideofile: ' + self.relativevideofile)
		debug('torrent_source: ' + self.torrent_source)
		debug('short_name: ' + self.short_name)
		debug('downloaded: ' + self.downloaded)
		debug('videotype: ' + self.videotype)

		if settings.run_script:
			self.process_params()
			self.run()

		if settings.remove_files:
			debug('Runner: remove_files')
			filesystem.remove(self.videofile)

		if float(self.downloaded) > 99:

			if settings.move_video and settings.copy_video_path and filesystem.exists(settings.copy_video_path):
				debug('Runner: move video')
				dest_path = filesystem.join(settings.copy_video_path, self.relativevideofile)

				if not filesystem.exists(filesystem.dirname(dest_path)):
					filesystem.makedirs(filesystem.dirname(dest_path))

				if not filesystem.exists(dest_path):
					#Move file if no exists
					filesystem.movefile(self.videofile, dest_path)
				else:
					filesystem.remove(self.videofile)

			if settings.copy_torrent and settings.copy_torrent_path and filesystem.exists(settings.copy_torrent_path):
				debug('Runner: copy torrent')
				dest_path = filesystem.join(settings.copy_torrent_path, filesystem.basename(self.torrent_path))
				filesystem.copyfile(self.torrent_path, dest_path)

	@staticmethod
	def get_addon_path():
		try:
			import xbmcaddon
			_ADDON_NAME = 'script.media.aggregator'
			_addon      = xbmcaddon.Addon(id=_ADDON_NAME)
			path = _addon.getAddonInfo('path').decode('utf-8')
			if path == 'Unavailable':
				raise Exception('Not in Kodi')
			return path
		except BaseException as e:
			log.print_tb(e)
			return filesystem.getcwd()

	@property
	def torrent(self):
		return self.torrent_path

	@property
	def videofile(self):
		return filesystem.join(self.settings.storage_path, self.relativevideofile)

	@property
	def videotype(self):
		base_path 		= self.settings.base_path().encode('utf-8')
		rel_path 		= urllib.unquote(self.params.get('path', ''))
		nfoFilename 	= urllib.unquote(self.params.get('nfo', ''))
		from nforeader import NFOReader
		nfoFullPath 	= NFOReader.make_path(base_path, rel_path, nfoFilename)
		if filesystem.exists(nfoFullPath):
			with filesystem.fopen(nfoFullPath, 'r') as nfo:
				s = nfo.read()
				if '<episodedetails>' in s:
					return 'episode'
				if '<movie>' in s:
					return 'movie'
		try:
			import xbmc
			return xbmc.getInfoLabel('ListItem.DBTYPE')
		except BaseException as e:
			log.print_tb(e)
			return ''

	@property
	def relativevideofile(self):
		with filesystem.fopen(self.torrent_path, 'rb') as torr:
			data = torr.read()

			if data is None:
				return self.playable_item['name']

			from bencode import BTFailure
			try:
				from bencode import bdecode
				decoded = bdecode(data)
			except BTFailure:
				debug("Can't decode torrent data (invalid torrent link?)")
				return self.playable_item['name']

			info = decoded['info']

			if 'files' in info:
				from base import TorrentPlayer
				return filesystem.join(TorrentPlayer.Name(info['name']), self.playable_item['name'])

		return self.playable_item['name']

	@property
	def torrent_source(self):
		import urllib
		return urllib.unquote(self.params['torrent'])

	@property
	def short_name(self):
		if 'anidub' in self.torrent_source:
			return 'anidub'
		if 'nnm-club' in self.torrent_source:
			return 'nnmclub'
		if 'hdclub' in self.torrent_source:
			return 'hdclub'
		if 'rutor' in self.torrent_source:
			return 'rutor'
		return None

	@property
	def downloaded(self):
		info = self.torrent_info
		if info is None:
			return 0

		try:
			return str(round(info['downloaded'] * 100 / info['size']))
		except BaseException as e:
			log.print_tb(e)
			return 0

	def process_params(self):
		for i, s in enumerate(self.command):
			if '%t' in s:
				self.command[i] = s.replace('%t', self.torrent)
			if '%f' in s:
				self.command[i] = s.replace('%f', self.videofile)
			if '%F' in s:
				self.command[i] = s.replace('%F', self.relativevideofile)
			if '%u' in s:
				self.command[i] = s.replace('%u', self.torrent_source)
			if '%s' in s:
				self.command[i] = s.replace('%s', self.short_name)
			if '%p' in s:
				self.command[i] = s.replace('%p', self.downloaded)
			if '%v' in s:
				self.command[i] = s.replace('%v', self.videotype)

			self.command[i] = self.command[i].encode('utf-8')

	def run(self):
		debug(self.command)
		import subprocess

		startupinfo = None
		u8runner = None

		if os.name == 'nt':
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= 1
			startupinfo.wShowWindow = 0
			u8runner = filesystem.abspath(filesystem.join(Runner.get_addon_path(), 'bin/u8runner.exe')).encode('mbcs')

		shell = self.command[0].startswith('@')
		if shell:
			self.command[0] = self.command[0][1:]

		try:
			subprocess.call(executable=u8runner, args=self.command, startupinfo=startupinfo, shell=shell)
		except OSError, e:
			debug(("Can't start %s: %r" % (str(self.command), e)))
		except BaseException as e:
			log.print_tb(e)

