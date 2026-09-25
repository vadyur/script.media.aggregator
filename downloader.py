import urllib.request, re, threading, os
from typing import Optional

from vdlib.util import filesystem


def _is_nnmclub(url: str) -> bool:
	return 'nnm-club' in url or 'nnmclub' in url


class Downloader(object):
	def __init__(self, url: str, saveDir: Optional[str] = None, extension: str = '', index: Optional[str] = None):
		self.url = url
		self.thread = None  # type: Optional[threading.Thread]
		self.saveDir = saveDir
		self.extension = extension
		self.index = index
		self.saved_to = None  # type: Optional[str]

	def log(self, msg: str) -> None:
		from vdlib.util.log import debug
		debug('Downloader: {}'.format(msg))

	def get_subdir_name(self) -> Optional[str]:
		if _is_nnmclub(self.url):
			return 'nnmclub'
		elif 'anidub' in self.url:
			return 'anidub'
		elif 'rutor' in self.url:
			return 'rutor'
		else:
			return None

	def get_post_index(self) -> Optional[str]:
		if self.index:
			return self.index
		return None

	def get_filename(self) -> str:
		path = filesystem.join(self.saveDir, self.get_subdir_name())
		if not filesystem.exists(path):
			filesystem.makedirs(path)
		return filesystem.join(self.saveDir, self.get_subdir_name(), self.get_post_index() + self.extension)

	def download(self) -> None:
		import shutil
		response = urllib.request.urlopen(self.url)
		with filesystem.fopen(self.get_filename(), 'wb') as f:
			shutil.copyfileobj(response, f)
		self.saved_to = self.get_filename()

	def start(self, in_background: bool = False) -> None:
		if in_background:
			self.log('Start downloading proccess in other thread')
			self.thread = threading.Thread(target=self.download)
			self.thread.start()
		else:
			self.log('Start downloading proccess in main thread')
			self.download()

	def is_finished(self) -> bool:
		if self.thread:
			return not self.thread.is_alive()
		else:
			return True

	def move_file_to(self, path: str) -> None:
		src = self.get_filename()

		dirname = filesystem.dirname(path)
		if not filesystem.exists(dirname):
			filesystem.makedirs(dirname)

		filesystem.copyfile(src, path)
		filesystem.remove(src)

		self.saved_to = path

		self.log('{} was moved to {}'.format(src, path))

class TorrentDownloader(Downloader):
	def __init__(self, url: str, saveDir: Optional[str], settings):
		Downloader.__init__(self, url, saveDir, '.torrent')
		self.index = self.get_post_index()
		self.settings = settings
		self._info_hash = None  # type: Optional[str]

	def get_post_index(self) -> Optional[str]:
		try:
			if _is_nnmclub(self.url):
				return re.search(r'\.php.+?t=(\d+)', self.url).group(1)
			elif 'anidub' in self.url:
				return re.search(r'/(\d+)-', self.url).group(1)
			elif 'rutor' in self.url:
				return re.search(r'torrent/(\d+)/', self.url).group(1)
			else:
				return None
		except BaseException as e:
			from vdlib.util.log import print_tb
			print_tb(e)
			return None

	def download(self) -> bool:
		def dnl():
			if _is_nnmclub(self.url):
				import nnmclub
				return nnmclub.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'anidub' in self.url:
				import anidub
				return anidub.download_torrent(self.url, self.get_filename(), self.settings)
			elif 'rutor' in self.url:
				import rutor
				return rutor.download_torrent(self.url, self.get_filename(), self.settings)

		try:
			if dnl():
				self.log('{} was downloaded to {}'.format(self.url, self.get_filename()))
				self.saved_to = self.get_filename()
				return True
		except:
			from vdlib.util.log import print_tb
			print_tb()

		return False

	def info_hash(self) -> Optional[str]:
		if not self._info_hash and self.is_finished():
			from vdlib.torrent.torrentplayer import TorrentPlayer
			tp = TorrentPlayer()
			tp.AddTorrent(self.saved_to)
			return tp.info_hash

		return self._info_hash
