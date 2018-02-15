import urllib2, requests, re, threading, filesystem, os

class Downloader(object):
	def __init__(self, url, saveDir = None, extension = '', index = None):
		self.url = url
		self.thread = None
		self.saveDir = saveDir
		self.extension = extension
		self.index = index

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

	def start(self, in_background = False):
		if in_background:
			self.thread = threading.Thread(target=self.download)
			self.thread.start()
		else:
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

class TorrentDownloader(Downloader):
	def __init__(self, url, saveDir, settings):
		Downloader.__init__(self, url, saveDir, '.torrent')
		self.index = self.get_post_index()
		self.settings = settings

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
			else:
				return None
		except BaseException as e:
			from log import debug, print_tb
			print_tb(e)
			return None

	def download(self):
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

		self.log('{} was downloaded to {}'.format(self.url, self.get_filename()))



