# -*- coding: utf-8 -*-

import log
from log import debug


import sys, xbmc, re, xbmcgui

import pyxbmct.addonwindow as pyxbmct

import filesystem
from base import STRMWriterBase, seeds_peers

class MyWindow(pyxbmct.AddonDialogWindow):

	def __init__(self, title, settings, links = []):
		# Вызываем конструктор базового класса.
		super(MyWindow, self).__init__(title)
		# Устанавливаем ширину и высоту окна, а также разрешение сетки (Grid):
		self.setGeometry(850, 550, 1, 1)

		self.settings = settings

		self.files = None
		self.left_menu = None
		self.list = pyxbmct.List('font14', _itemHeight=120)
		self.placeControl(self.list, 0, 0)

		for item in links:
			s = ''
			try:
				link = item['link']
				if 'anidub' in link:
					s += '[AniDUB] '
				elif 'nnm-club' in link:
					s += '[NNM-Club] '
				elif 'hdclub' in link:
					s += '[HDclub] '
				elif 'rutor' in link:
					s += '[rutor] '
				elif 'soap4' in link:
					s += '[soap4me] '
			except:
				pass
			try:
				s += item['full_title']
			except:
				pass
			try:
				s += '\n' + u'Видео: ' + item['video']
			except:
				pass
			try:
				s += '\n' + u'Перевод: ' + item['translate']
				#print s
			except:
				pass
			try:
				#info = seeds_peers(item)
				s +=  '\n' + u'Сиды: %d        пиры: %d' % (item['seeds'], item['peers'])
			except BaseException as e:
				debug(str(e))
				pass

			if s != '':
				li = xbmcgui.ListItem(s)
				li.setProperty('link', link)
				self.list.addItem(li)
			#list.addItem('Item 1\nNew line')
			#list.addItem('Item 2\nNew line')
			#list.addItem('Item 3\nNew line\nAdd line')

		kodi_ver_major = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])

		if kodi_ver_major < 16:
			li = xbmcgui.ListItem(u'НАСТРОЙКИ...')
			li.setProperty('link', 'plugin://script.media.aggregator/?action=settings')
			self.list.addItem(li)

			# (u'Смотрите также', 'Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % str(item.tmdb_id())),
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

		path = self.download_torrent(link)

		# +++

		if self.settings.copy_torrent_path:
			li = xbmcgui.ListItem(u'Копировать торрент')
			li.setProperty('link', link)
			li.setProperty('path', path)
			li.setProperty('action', 'copy_torrent')
			self.left_menu.addItem(li)

		# +++

		self.setFocus(self.left_menu)
		self.connect(self.left_menu, self.select_menu_item)

	def select_menu_item(self):
		cursel = self.left_menu.getSelectedItem()
		action = cursel.getProperty('action')
		if action == 'copy_torrent':
			self.copy_torrent(cursel.getProperty('path'))
		self.show_list()

	def copy_torrent(self, torrent_path):
		settings = self.settings
		if settings.copy_torrent_path and filesystem.exists(settings.copy_torrent_path):
			dest_path = filesystem.join(self.settings.copy_torrent_path, filesystem.basename(torrent_path))
			filesystem.copyfile(torrent_path, dest_path)

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
			if dbtype == 'movies':
				jsno = {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": { "properties": ["file"], "movieid": dbid }, "id": 1}
				result = json.loads(xbmc.executeJSONRPC(json.dumps(jsno)))
				path = result[u'result'][u'moviedetails'][u'file']
			if dbtype == 'tvshows' or dbtype == 'inprogresstvshows':
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

def main():
	import vsdbg
	vsdbg._bp()

	path, name = get_path_name()
		
	import player
	settings = player.load_settings()

	import xbmcvfs, os
	tempPath = xbmc.translatePath('special://temp')
	if xbmcvfs.exists(path+'.alternative'):
		debug('path exists')
		xbmcvfs.copy(path, os.path.join(tempPath, name))
		xbmcvfs.copy(path + '.alternative', os.path.join(tempPath, name + '.alternative'))
		path = os.path.join(tempPath, name)
	else:
		return

	links = STRMWriterBase.get_links_with_ranks(path.decode('utf-8'), settings, use_scrape_info=True)

	window = MyWindow(settings.addon_name, settings=settings, links=links)
	window.doModal()

	debug(window.has_choice)
	debug(window.has_select_file)

	if not window.has_choice and not window.has_select_file:
		del window
		return

	cursel = window.list.getSelectedItem()
	debug(cursel.getLabel())
	link = cursel.getProperty('link')
	debug(link)

	if link == 'plugin://script.media.aggregator/?action=settings':
		xbmc.executebuiltin('Addon.OpenSettings(script.media.aggregator)')
		del window
		return

	if link == 'plugin://script.media.aggregator/?action=show_similar':
		from context_show_similar import show_similar
		if show_similar():
			del window
			return

	if link == 'plugin://script.media.aggregator/?action=add_media':
		from context_get_sources import get_sources
		get_sources(settings)
		return

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
			dst_link = re.sub(pattern, 'torrent=' + match.group(1) + '&', str(src_link)) + '&onlythis=true'
			debug(dst_link)

			if selected_file:
				#import urllib
				#from tvshowapi import cutStr
				#dst_link += '&cutName=' + urllib.quote(cutStr(selected_file))
				dst_link += '&index=' + str(selected_file)

			xbmc.executebuiltin('xbmc.PlayMedia(' + dst_link + ')')

	if tempPath in path:
		xbmcvfs.delete(path)
		xbmcvfs.delete(path + '.alternative')

if __name__ == '__main__':
	main()