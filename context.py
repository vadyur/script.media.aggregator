# -*- coding: utf-8 -*-

import log
from log import debug


import sys, xbmc, re, xbmcgui

import pyxbmct.addonwindow as pyxbmct

import filesystem
from base import STRMWriterBase, seeds_peers

seeds_peers_fmt = u'[COLOR=FF5AC3C6][B]Сиды[/B]:[/COLOR] %d        [COLOR=FF5AC3C6][B]пиры[/B]:[/COLOR] %d'

def colorify(text, sub, color):
	return text.replace(str(sub), '[COLOR={}]{}[/COLOR]'.format(color, sub))
def boldify(text, sub):
	return text.replace(str(sub), '[B]{}[/B]'.format(sub))

class MyWindow(pyxbmct.AddonDialogWindow):

	def fill_list(self):
		for item in self.make_links():
			s = '' if item.get('rank', 1) >= 1 else '* '
			#s += str(item.get('rank', '')) + ' '
			try:
				link = item['link']
				s += '[COLOR=FFFF6666][B]'
				if 'anidub' in link:
					s += '[AniDUB] '
				elif 'nnm-club' in link:
					s += '[NNM-Club] '
				elif 'hdclub' in link:
					s += '[EliteHD] '
				elif 'bluebird' in link:
					s += '[BlueBird-HD] '
				elif 'rutor' in link:
					s += '[rutor] '
				elif 'soap4' in link:
					s += '[soap4me] '
				elif 'kinohd' in link:
					s += '[KinoHD] '
				s += '[/B][/COLOR]'
			except:
				pass
			try:
				s += item['full_title']
			except:
				pass
			try:
				s += '\n' + u'[COLOR=FF5AC3C6][B]Видео[/B]:[/COLOR] ' + item['video']
			except:
				pass
			try:
				s += '\n' + u'[COLOR=FF5AC3C6][B]Перевод[/B]:[/COLOR] ' + item['translate']
				#print s
			except:
				pass
			try:
				#info = seeds_peers(item)
				s +=  '\n' + seeds_peers_fmt % (item['seeds'], item['peers'])
			except BaseException as e:
				#debug(str(e))
				pass

			if s != '':
				for sub in [1920, 1080, 1280, 720, 3840, 2160, 540, 480, 360]:
					s = colorify(s, sub, 'white')
					s = boldify(s, sub)

				li = xbmcgui.ListItem(s)
				li.setProperty('link', link)
				self.list.addItem(li)

	def __init__(self, title, settings, links):
		# Вызываем конструктор базового класса.
		super(MyWindow, self).__init__(title)
		# Устанавливаем ширину и высоту окна, а также разрешение сетки (Grid):
		self.setGeometry(1280, 720, 1, 1)

		self.settings = settings

		self.files = None
		self.left_menu = None
		self.list = pyxbmct.List('font14', _itemHeight=120)
		self.placeControl(self.list, 0, 0)

		self.make_links = links

		self.fill_list()

		links.set_reload(self.reload)

		kodi_ver_major = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])

		if kodi_ver_major < 16:
			li = xbmcgui.ListItem(u'НАСТРОЙКИ...')
			li.setProperty('link', 'plugin://script.media.aggregator/?action=settings')
			self.list.addItem(li)

			li = xbmcgui.ListItem(u'СМОТРИТЕ ТАКЖЕ...')
			li.setProperty('link', 'plugin://script.media.aggregator/?action=show_similar')
			self.list.addItem(li)

			li = xbmcgui.ListItem(u'ПОИСК ИСТОЧНИКОВ...')
			li.setProperty('link', 'plugin://script.media.aggregator/?action=add_media')
			self.list.addItem(li)

			pathUnited = 'special://home/addons/plugin.video.united.search'
			pathUnited = xbmc.translatePath(pathUnited)
			if filesystem.exists(pathUnited.decode('utf-8')):
				li = xbmcgui.ListItem(u'UNITED SEARCH...')
				li.setProperty('link', 'plugin://script.media.aggregator/?action=united_search')
				self.list.addItem(li)
		

		self.setFocus(self.list)
		self.connect(self.list, self.make_choice)

		self.connect(pyxbmct.ACTION_MOVE_RIGHT, self.go_right)
		self.connect(pyxbmct.ACTION_MOVE_LEFT, self.go_left)

		# Связываем клавиатурное действие с методом.
		self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
		self.has_choice = False
		self.has_select_file = False

	def reload(self, item):

		#import xbmcgui
		#xbmcgui.Dialog().ok(self.settings.addon_name, "Reload")

		def find_listitem(item):
			for index in xrange(self.list.size()):
				li = self.list.getListItem(index)
				if li.getProperty('link') == item['link']:
					return li
			return None

		if 'seeds' in item and 'peers' in item:
			li = find_listitem(item)
			if li:
				s = li.getLabel()
				if not isinstance(s, unicode):
					s = s.decode('utf-8')
				s +=  '\n' + seeds_peers_fmt % (item['seeds'], item['peers'])
				li.setLabel(s)

	def go_left(self):
		if self.files:
			self.show_list()
		else:
			self.show_menu()

	def go_right(self):
		if self.left_menu:
			self.show_list()
		else:
			self.show_files()

	def show_menu(self):
		if self.left_menu:
			return

		self.left_menu = pyxbmct.List('font14')
		self.placeControl(self.left_menu, 0, 0)

		link = self.cursel_link()

		self.list.setVisible(False)

		#path = self.download_torrent(link)
		#choice_path = path.replace('.torrent', '.choice')
		from downloader import TorrentDownloader
		import urllib
		torr_downloader = TorrentDownloader(urllib.unquote(link), None, self.settings)
		choice_path = filesystem.join(self.settings.torrents_path(), torr_downloader.get_subdir_name(), torr_downloader.get_post_index() + '.choice')


		# +++

		if self.settings.copy_torrent_path:
			li = xbmcgui.ListItem(u'Копировать торрент')
			li.setProperty('link', link)
			#li.setProperty('path', path)
			li.setProperty('action', 'copy_torrent')
			self.left_menu.addItem(li)

		if filesystem.exists(choice_path):
			li = xbmcgui.ListItem(u'Отменить выбор')
			li.setProperty('link', link)
			li.setProperty('path', choice_path)
			li.setProperty('action', 'cancel_choice')
		else:
			li = xbmcgui.ListItem(u'Запомнить выбор')
			li.setProperty('link', link)
			li.setProperty('path', choice_path)
			li.setProperty('action', 'remember_choice')
		self.left_menu.addItem(li)

		# +++

		self.setFocus(self.left_menu)
		self.connect(self.left_menu, self.select_menu_item)

	def select_menu_item(self):
		cursel = self.left_menu.getSelectedItem()
		action = cursel.getProperty('action')
		if action == 'copy_torrent':
			link = cursel.getProperty('link')
			def go_copy_torrent():
				path = self.download_torrent(link)
				debug(path)
				self.copy_torrent(path)

			import threading
			self.thread = threading.Thread(target=go_copy_torrent)
			self.thread.start()
			
		elif action == 'remember_choice':
			self.remember_choice(cursel.getProperty('path'))
		elif action == 'cancel_choice':
			self.cancel_choice(cursel.getProperty('path'))
		self.show_list()

	def copy_torrent(self, torrent_path):
		settings = self.settings
		if settings.copy_torrent_path and filesystem.exists(settings.copy_torrent_path):
			dest_path = filesystem.join(self.settings.copy_torrent_path, filesystem.basename(torrent_path))
			filesystem.copyfile(torrent_path, dest_path)

	def remember_choice(self, choice_path):
		with filesystem.fopen(choice_path, 'w'):
			pass

		self.list.reset()
		self.fill_list()

	def cancel_choice(self, choice_path):
		filesystem.remove(choice_path)
		self.list.reset()
		self.fill_list()

	def show_list(self):
		self.list.setVisible(True)
		self.setFocus(self.list)

		if self.files:
			self.files.setVisible(False)
			del self.files
			self.files = None

		if self.left_menu:
			self.left_menu.setVisible(False)
			del self.left_menu
			self.left_menu = None

	def cursel_link(self):
		cursel = self.list.getSelectedItem()
		debug(cursel.getLabel())
		link = cursel.getProperty('link')

		match = re.search('torrent=(.+)&', str(link))
		if not match:
			pattern2 = 'torrent=(.+)'
			match = re.search(pattern2, str(link))

		if match:
			link = match.group(1)

		return link

	def download_torrent(self, link):
		tempPath = xbmc.translatePath('special://temp').decode('utf-8')
		from downloader import TorrentDownloader
		import player
		settings = self.settings
		import urllib
		torr_downloader = TorrentDownloader(urllib.unquote(link), tempPath, settings)
		path = filesystem.join(settings.torrents_path(), torr_downloader.get_subdir_name(), torr_downloader.get_post_index() + '.torrent')
		if not filesystem.exists(path):
			torr_downloader.download()
			path = torr_downloader.get_filename()

		debug(path)

		return path

	def show_files(self):
		if self.files:
			return

		self.files = pyxbmct.List('font14')
		self.placeControl(self.files, 0, 0)

		link = self.cursel_link()

		self.list.setVisible(False)

		path = self.download_torrent(link)

		if filesystem.exists(path):
			import base
			player = base.TorrentPlayer()
			player.AddTorrent(path)
			data = player.GetLastTorrentData()
			if data:
				for f in data['files']:
					try:
						li = xbmcgui.ListItem(str(f['size'] / 1024 / 1024) + u' МБ | ' + f['name'])
					except:
						li = xbmcgui.ListItem(f['name'])
					li.setProperty('index', str(f['index']))
					self.files.addItem(li)

		self.setFocus(self.files)
		self.connect(self.files, self.select_file)

	def select_file(self):
		debug('select_file')
		self.has_select_file = True
		self.close()

	def make_choice(self):
		debug('make choice')
		self.has_choice = True
		self.close()


def debug_info_label(s):
	debug('%s: ' % s + xbmc.getInfoLabel(s))
	debug('%s: ' % s + sys.listitem.getProperty(s.split('.')[-1]))

def get_path_name():
	path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
	name = xbmc.getInfoLabel('ListItem.FileName')

	if path and name:
		return path, name

	dbpath = sys.listitem.getfilename()
	
	if not path or not name:
		if not dbpath.startswith('videodb://') and dbpath.endswith('.strm'):
			path = dbpath
	
	if path and not name:
		name = path.replace('\\', '/').split('/')[-1]
	
	if not path or not name:
		if dbpath.startswith('videodb://'):
			dbpath = dbpath.split('://')[-1]
			dbpath = dbpath.split('?')[0]
			dbpath = dbpath.rstrip('/')
			parts = dbpath.split('/')
			dbtype = parts[0]
			dbid = int(parts[-1])
	
			import json
			path = None
			if 'movies' in dbtype:
				jsno = {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": { "properties": ["file"], "movieid": dbid }, "id": 1}
				result = json.loads(xbmc.executeJSONRPC(json.dumps(jsno)))
				path = result[u'result'][u'moviedetails'][u'file']
			if 'tvshows' in dbtype:
				if xbmc.getInfoLabel('ListItem.DBTYPE') == 'episode':
					jsno = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": { "properties": ["file"], "episodeid": dbid }, "id": 13}
					res_type = 'episodedetails'
				else:
					jsno = {"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": { "properties": ["file"], "tvshowid": dbid }, "id": 13}
					res_type = 'tvshowdetails'
				result = json.loads(xbmc.executeJSONRPC(json.dumps(jsno)))
				path = result[u'result'][res_type][u'file']
	
			try:
				if path:
					path = path.encode('utf-8')
			except UnicodeDecodeError:
				pass
	
			name = path.replace('\\', '/').split('/')[-1]
	return path, name

def main(settings=None, path=None, name=None, run=None):

	import time
	main.start_time = time.time()

	def stage(n):
		"""
		now = time.time()
		debug('stage: {} ({} msec)'.format(n, (now - main.start_time)))
		main.start_time = now
		"""

	stage(0)

	if not path or not name:
		path, name = get_path_name()

	stage(1)

	if not settings:		
		import player
		settings = player.load_settings()

	stage(2)

	import xbmcvfs, os
	tempPath = xbmc.translatePath('special://temp')
	if xbmcvfs.exists(path+'.alternative'):
		debug('path exists')
		xbmcvfs.copy(path, os.path.join(tempPath, name))
		xbmcvfs.copy(path + '.alternative', os.path.join(tempPath, name + '.alternative'))
		path = os.path.join(tempPath, name)
	else:
		return False

	class Links():
		def __init__(self):
			self.reload = None
			self._links = result = STRMWriterBase.get_links_with_ranks(path.decode('utf-8'), settings, use_scrape_info=False)

		def	__call__(self):
			return self._links

		def set_reload(self, reload):
			self.reload = reload
			import threading
			self.thread = threading.Thread(target=self.do_get_seeds_peers )
			self.thread.start()

		def do_get_seeds_peers(self):
			from base import seeds_peers
			for item in self._links:
				if self.reload:
					sp = seeds_peers(item)
					item = dict(item, **sp)
					self.reload(item)

		def close(self):
			self.reload = None

	stage(3)

	links = Links()

	stage(4)

	window = MyWindow(settings.addon_name, settings=settings, links=links)

	stage(5)

	window.doModal()

	links.close()

	debug(window.has_choice)
	debug(window.has_select_file)

	if not window.has_choice and not window.has_select_file:
		del window
		return True

	cursel = window.list.getSelectedItem()
	debug(cursel.getLabel())
	link = cursel.getProperty('link')
	debug(link)

	if link == 'plugin://script.media.aggregator/?action=settings':
		xbmc.executebuiltin('Addon.OpenSettings(script.media.aggregator)')
		del window
		return True

	if link == 'plugin://script.media.aggregator/?action=show_similar':
		from context_show_similar import show_similar
		if show_similar():
			del window
			return True

	if link == 'plugin://script.media.aggregator/?action=add_media':
		from context_get_sources import get_sources
		get_sources(settings)
		return True

	if link == 'plugin://script.media.aggregator/?action=united_search':
		import context_united_search

	selected_file = None
	if window.has_select_file:
		#selected_file = window.files.getSelectedItem().getLabel()
		selected_file = window.files.getSelectedItem().getProperty('index')

	del window

	with filesystem.fopen(path.decode('utf-8'), 'r') as strm:
		src_link = strm.read()
		debug(src_link)
		pattern = 'torrent=(.+?)&'
		match = re.search(pattern, str(link))
		if not match:
			pattern2 = 'torrent=(.+)'
			match = re.search(pattern2, str(link))

		if match:
			torr = match.group(1)
			dst_link = re.sub(pattern, 'torrent=' + torr + '&', str(src_link)) + '&onlythis=true'
			debug(dst_link)

			if selected_file:
				dst_link += '&index=' + str(selected_file)

			if run:
				if selected_file:				
					run(torr, int(selected_file))
				else:
					run(torr)
			else:
				xbmc.executebuiltin('xbmc.PlayMedia(' + dst_link + ')')

	if tempPath in path:
		xbmcvfs.delete(path)
		xbmcvfs.delete(path + '.alternative')

	return True

if __name__ == '__main__':
	#import vsdbg
	#vsdbg._bp()
	main()