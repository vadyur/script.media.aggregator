# -*- coding: utf-8 -*-

from vdlib.util import log
from vdlib.util.log import debug

import os
import urllib.parse

from vdlib.util import filesystem
from vdlib.kodi.compat import translatePath
from vdlib.torrent.torrentplayer import TorrentPlayer
from vdlib.torrent.bencodepy import bdecode, BencodeDecodeError

class Runner(object):
	def __init__(self, settings, params, playable_item, torrent_info, torrent_path, info_hash):
		self.command = settings.script_params.split(' ')
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
		debug('downloaded: ' + str(self.downloaded))
		debug('videotype: ' + self.videotype)

		if settings.run_script:
			self.process_params()
			self.run()

		if settings.remeber_watched and float(self.downloaded) > 99:
			choice_path = torrent_path.replace('.torrent', '.choice')
			filesystem.touch(choice_path)

		if float(self.downloaded) > 99:
			if settings.copy_torrent and settings.copy_torrent_path and filesystem.exists(settings.copy_torrent_path):
				self.copy_torrent()

	def copy_torrent(self) -> None:
		debug('Runner: copy torrent')
		dest_path = filesystem.join(self.settings.copy_torrent_path, filesystem.basename(self.torrent_path))
		filesystem.copyfile(self.torrent_path, dest_path)

	@staticmethod
	def get_addon_path() -> str:
		try:
			import xbmcaddon
			_ADDON_NAME = 'script.media.aggregator'
			_addon      = xbmcaddon.Addon(id=_ADDON_NAME)
			path = _addon.getAddonInfo('path')
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
	def storage_path(self) -> str:
		result = getattr(self.settings, 'storage_path', '')
		if not result:
			result = translatePath('special://temp')
		return result


	@property
	def videofile(self):
		return filesystem.join(self.storage_path, self.relativevideofile)

	@property
	def videotype(self) -> str:
		base_path 		= self.settings.base_path()
		rel_path 		= urllib.parse.unquote(self.params.get('path', ''))
		nfoFilename 	= urllib.parse.unquote(self.params.get('nfo', ''))
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
	def relativevideofile(self) -> str:
		with filesystem.fopen(self.torrent_path, 'rb') as torr:
			data = torr.read()

			if data is None:
				return self.playable_item['name']

			try:
				decoded = bdecode(data)
			except BencodeDecodeError:
				debug("Can't decode torrent data (invalid torrent link?)")
				return self.playable_item['name']

			info = decoded[b'info']

			if b'files' in info:
				return filesystem.join(TorrentPlayer.Name(info[b'name']), self.playable_item['name'])

		return self.playable_item['name']

	@property
	def torrent_source(self) -> str:
		return urllib.parse.unquote(self.params['torrent'])

	@property
	def short_name(self) -> str:
		if 'anidub' in self.torrent_source:
			return 'anidub'
		if 'nnm-club' in self.torrent_source or 'nnmclub' in self.torrent_source:
			return 'nnmclub'
		if 'rutor' in self.torrent_source:
			return 'rutor'
		return ''

	@property
	def downloaded(self) -> str:
		info = self.torrent_info
		if info is None:
			return '0'

		try:
			return str(round(info['downloaded'] * 100 / info['size']))
		except BaseException as e:
			log.print_tb(e)
			return '0'

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

	def run(self) -> None:
		debug(self.command)
		import subprocess

		# Python 3 передаёт юникодные аргументы сам, обёртка u8runner.exe больше не нужна
		startupinfo = None
		if os.name == 'nt':
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= 1
			startupinfo.wShowWindow = 0

		shell = self.command[0].startswith('@')
		if shell:
			self.command[0] = self.command[0][1:]

		try:
			subprocess.call(self.command, startupinfo=startupinfo, shell=shell)
		except OSError as e:
			debug(("Can't start %s: %r" % (str(self.command), e)))
		except BaseException as e:
			log.print_tb(e)
