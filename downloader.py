import urllib2, requests, re, threading, filesystem, os

class Downloader(object):
	def __init__(self, url, saveDir = None, extension = '', index = None):
		self.url = url
		self.thread = None
		self.saveDir = saveDir
		self.extension = extension
		self.index = index
		self.saved_to = None

	def log(self, msg):
		from log import debug
		debug('Downloader: {}'.format(msg))

	def get_subdir_name(self):
		if 'nnm-club' in self.url:
			return 'nnmclub'
		elif 'hdclub' in self.url:
			return 'elitehd'
		elif 'bluebird' in self.url:
			return 'bluebird'
		elif 'anidub' in self.url:
			return 'anidub'
		elif 'rutor' in self.url:
			return 'rutor'
		elif 'soap4' in self.url:
			return 'soap4'
		elif 'kinohd' in self.url:
			return 'kinohd'
		else:
			return None

	def get_post_index(self):
		if self.index:
			return self.index

	def get_filename(self):
		path = filesystem.join(self.saveDir, self.get_subdir_name())
		if not filesystem.exists(path):
			filesystem.makedirs(path)
		return filesystem.join(self.saveDir, self.get_subdir_name(), self.get_post_index() + self.extension)

	def download(self):
		import shutil
		response = urllib2.urlopen(self.url)
		with filesystem.fopen(self.get_filename(), 'wb') as f:
			shutil.copyfileobj(response, f)
		self.saved_to = self.get_filename()

	def start(self, in_background = False):
		if in_background:
			self.log('Start downloading proccess in other thread')
			self.thread = threading.Thread(target=self.download)
			self.thread.start()
		else:
			self.log('Start downloading proccess in main thread')
			self.download()

	def is_finished(self):
		if self.thread:
			return not self.thread.isAlive()
		else:
			return True

	def move_file_to(self, path):
		src = self.get_filename()

		dirname = filesystem.dirname(path)
		if not filesystem.exists(dirname):
			filesystem.makedirs(dirname)

		filesystem.copyfile(src, path)
		filesystem.remove(src)

		self.saved_to = path

		self.log('{} was moved to {}'.format(src, path))

class TorrentDownloader(Downloader):
	def __init__(self, url, saveDir, settings):
		Downloader.__init__(self, url, saveDir, '.torrent')
		self.index = self.get_post_index()
		self.settings = settings
		self._info_hash = None

	def get_post_index(self):
		try:
			if 'nnm-club' in self.url:
				return re.search(r'\.php.+?t=(\d+)', self.url).group(1)
			elif 'hdclub' in self.url:
				return re.search(r'\.php.+?id=(\d+)', self.url).group(1)
			elif 'bluebird' in self.url:
				return re.search(r'\.php.+?id=(\d+)', self.url).group(1)
			elif 'anidub' in self.url:
				return re.search(r'/(\d+)-', self.url).group(1)
			elif 'rutor' in self.url:
				return re.search(r'torrent/(\d+)/', self.url).group(1)
			elif 'soap4' in self.url:
				return re.search(r'/(\d+).torrent', self.url).group(1)
			elif 'kinohd' in self.url:
				# http://kinohd.net/1080p/8279-tohya-928pot886b-bcex-itonya-2017.html
				part = self.url.split('/')[-1]
				return re.search(r'^(\d+)', part).group(1)
			else:
				return None
		except BaseException as e:
			from log import debug, print_tb
			print_tb(e)
			return None

	def download(self):
		def dnl():
			if 'nnm-club' in self.url:
				import nnmclub
				return nnmclub.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'hdclub' in self.url:
				import hdclub
				return hdclub.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'bluebird' in self.url:
				import bluebird
				return bluebird.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'anidub' in self.url:
				import anidub
				return anidub.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'rutor' in self.url:
				import rutor
				return rutor.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'soap4' in self.url:
				import soap4me
				return soap4me.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'kinohd' in self.url:
				import kinohd
				return kinohd.download_torrent(self.url, self.get_filename(), self.settings)

		if dnl():
			self.log('{} was downloaded to {}'.format(self.url, self.get_filename()))
			self.saved_to = self.get_filename()
			return True
		
		return False

	def info_hash(self):
		if not self._info_hash and self.is_finished():
			from base import TorrentPlayer
			tp = TorrentPlayer()
			tp.AddTorrent(self.saved_to)
			return tp.info_hash

		return self._info_hash
