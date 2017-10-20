# -*- coding: utf-8 -*-

import log
from log import debug


import os
import urllib

import filesystem

class Runner(object):
	def __init__(self, settings, params, playable_item, torrent_info, torrent_path, info_hash):
		self.command = settings.script_params.split(u' ')
		self.settings = settings
		self.params = params
		self.torrent_info = torrent_info
		self.torrent_path = torrent_path
		self.playable_item = playable_item

		self.resume_file = filesystem.join(self.settings.torrents_path(), info_hash + '.resume')

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

		if settings.remove_files:
			debug('Runner: remove_files')
			if filesystem.exists(self.videofile):
				filesystem.remove(self.videofile)

		if float(self.downloaded) > 99 and self.all_torrent_files_exists():

			if settings.move_video and settings.copy_video_path and filesystem.exists(settings.copy_video_path):
				self.move_video_files()

			if settings.copy_torrent and settings.copy_torrent_path and filesystem.exists(settings.copy_torrent_path):
				self.copy_torrent()

	def copy_torrent(self):
		debug('Runner: copy torrent')
		dest_path = filesystem.join(self.settings.copy_torrent_path, filesystem.basename(self.torrent_path))
		filesystem.copyfile(self.torrent_path, dest_path)

	def move_video_files(self):
		debug('Runner: move video')
		for file in self.get_relative_torrent_files_list():
			dest_path = filesystem.join(self.settings.copy_video_path, file)

			if not filesystem.exists(filesystem.dirname(dest_path)):
				filesystem.makedirs(filesystem.dirname(dest_path))

			src_path = filesystem.join(self.storage_path, file)
			if not filesystem.exists(src_path):
				continue

			if not filesystem.exists(dest_path):
				# Move file if no exists
				filesystem.movefile(src_path, dest_path)
			else:
				filesystem.remove(src_path)

			self.change_resume_file(self.settings.copy_video_path)

	def change_resume_file(self, dest):
		if filesystem.exists(self.resume_file):
			data = None
			with filesystem.fopen(self.resume_file, 'rb') as resume:
				from bencode import BTFailure
				try:
					from bencode import bdecode, bencode
					decoded = bdecode(resume.read())
					decoded['save_path'] = dest.encode('utf-8')
					data = bencode(decoded)

				except BTFailure:
					pass

			if data:
				with filesystem.fopen(self.resume_file, 'wb') as resume:
					resume.write(data)

	def all_torrent_files_exists(self):
		from base import TorrentPlayer
		tp = TorrentPlayer()
		tp.AddTorrent(self.torrent)
		data = tp.GetLastTorrentData()
		files = data['files']

		for item in files:
			path = filesystem.join(self.storage_path, data['name'], item['name'])
			debug(u'all_torrent_files_exists: ' + path)
			if not filesystem.exists(path):
				path = filesystem.join(self.settings.copy_video_path, data['name'], item['name'])
				debug(u'all_torrent_files_exists: ' + path)
				if not filesystem.exists(path):
					debug(u'all_torrent_files_exists: not found')
					return False

		debug(u'all_torrent_files_exists: Ok')
		return True


	def get_relative_torrent_files_list(self):
		from base import TorrentPlayer

		tp = TorrentPlayer()
		tp.AddTorrent(self.torrent)
		data = tp.GetLastTorrentData()
		files = data['files']

		return [filesystem.join(data['name'], item['name']) for item in files]

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
	def storage_path(self):
		result = self.settings.storage_path
		if result == '':
			import xbmc
			result = xbmc.translatePath('special://temp').decode('utf-8')
		return result


	@property
	def videofile(self):
		return filesystem.join(self.storage_path, self.relativevideofile)

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
			return 'elitehd'
		if 'bluebird' in self.torrent_source:
			return 'bluebird'
		if 'rutor' in self.torrent_source:
			return 'rutor'
		if 'soap4' in self.torrent_source:
			return 'soap4me'
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


class TestRunner(Runner):
	def __init__(self):
		pass


def test_resume(tr):
	dest = u'/mnt/videocache/фываолдж'
	Runner.change_resume_file(tr, dest)


def test_get_relative_torrent_files_list(tr):
	l = Runner.get_relative_torrent_files_list(tr)
	for f in l:
		print f


if __name__ == '__main__':
	tr = TestRunner()
	tr.resume_file = r'c:\Bin\626bbfbb61755200069486609d66e53146483ebe.resume'
	tr.torrent_path = r'c:\Users\vd\AppData\Roaming\Kodi\userdata\addon_data\script.media.aggregator\nnmclub\507983.torrent'

	test_resume(tr)

	#test_get_relative_torrent_files_list(tr)