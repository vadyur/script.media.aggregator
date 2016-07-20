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
		self.list = pyxbmct.List('font14', _itemHeight=100)
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

		li = xbmcgui.ListItem(u'НАСТРОЙКИ...')
		li.setProperty('link', 'plugin://script.media.aggregator/?action=settings')
		self.list.addItem(li)

		# (u'Смотрите также', 'Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % str(item.tmdb_id())),
		li = xbmcgui.ListItem(u'СМОТРИТЕ ТАКЖЕ...')
		li.setProperty('link', 'plugin://script.media.aggregator/?action=show_similar')
		self.list.addItem(li)

		self.setFocus(self.list)
		self.connect(self.list, self.make_choice)

		self.connect(pyxbmct.ACTION_MOVE_RIGHT, self.show_files)
		self.connect(pyxbmct.ACTION_MOVE_LEFT, self.show_list)

		# Связываем клавиатурное действие с методом.
		self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
		self.has_choice = False
		self.has_select_file = False

	def show_list(self):
		self.list.setVisible(True)
		self.setFocus(self.list)

		if self.files:
			self.files.setVisible(False)
			del self.files
			self.files = None

	def show_files(self):
		if self.files:
			return

		self.files = pyxbmct.List('font14')
		self.placeControl(self.files, 0, 0)

		cursel = self.list.getSelectedItem()
		debug(cursel.getLabel())
		link = cursel.getProperty('link')

		match = re.search('torrent=(.+)&', str(link))
		if not match:
			pattern2 = 'torrent=(.+)'
			match = re.search(pattern2, str(link))

		if match:
			link = match.group(1)

		self.list.setVisible(False)

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
		if filesystem.exists(path):
			import base
			player = base.TorrentPlayer()
			player.AddTorrent(path)
			data = player.GetLastTorrentData()
			if data:
				for f in data['files']:
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

def main():
	debug_info_label('ListItem.FileName')
	debug_info_label('ListItem.Path')
	debug_info_label('ListItem.FileExtension')
	debug_info_label('ListItem.FileNameAndPath')
	debug_info_label('ListItem.DBID')		# movie id)
	debug_info_label('ListItem.IMDBNumber')

	debug_info_label('Container.FolderPath')

	# import rpdb2
	# rpdb2.start_embedded_debugger('pw')

	import player
	settings = player.load_settings()

	path = xbmc.getInfoLabel('ListItem.FileNameAndPath')
	name = xbmc.getInfoLabel('ListItem.FileName')
	
	import xbmcvfs, os
	tempPath = xbmc.translatePath('special://temp')
	if xbmcvfs.exists(path+'.alternative'):
		debug('path exists')
		xbmcvfs.copy(path, os.path.join(tempPath, name))
		xbmcvfs.copy(path + '.alternative', os.path.join(tempPath, name + '.alternative'))
		path = os.path.join(tempPath, name)

	links = STRMWriterBase.get_links_with_ranks(path.decode('utf-8'), settings, use_scrape_info=True)

	window = MyWindow('Media Aggregator', settings=settings, links=links)
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
		imdb_id = xbmc.getInfoLabel('ListItem.IMDBNumber')
		type='movie'

		if not imdb_id and xbmc.getInfoLabel('ListItem.DBTYPE') == 'episode':
			from nforeader import NFOReader
			nfo_path = xbmc.getInfoLabel('ListItem.FileNameAndPath').replace('.strm', '.nfo').decode('utf-8')
			debug(nfo_path)
			rd = NFOReader(nfo_path, '')
			tvs_rd = rd.tvs_reader()
			imdb_id = tvs_rd.imdb_id()
			type='tv'

		if imdb_id:
			from movieapi import MovieAPI
			res = MovieAPI.tmdb_by_imdb(imdb_id, type)
			debug(res)
			if res and len(res) > 0:
				tmdb_id = res[0].tmdb_id()
				xbmc.executebuiltin('Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % tmdb_id)
				del window
				return

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