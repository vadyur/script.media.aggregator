# -*- coding: utf-8 -*-

import sys, xbmc, re, xbmcgui

import pyxbmct.addonwindow as pyxbmct

import filesystem
from base import STRMWriterBase


class MyWindow(pyxbmct.AddonDialogWindow):
	def __init__(self, title='', links = []):
		# Вызываем конструктор базового класса.
		super(MyWindow, self).__init__(title)
		# Устанавливаем ширину и высоту окна, а также разрешение сетки (Grid):
		self.setGeometry(850, 550, 1, 1)

		self.files = None
		self.list = pyxbmct.List('font14', _itemHeight=80)
		self.placeControl(self.list, 0, 0)

		for item in links:
			try:
				s = ''
				link = item['link']
				if 'anidub' in link:
					s += '[AniDUB] '
				elif 'nnm-club' in link:
					s += '[NNM-Club] '
				elif 'hdclub' in link:
					s += '[HDclub] '
				s += item['full_title']
				s += '\n' + u'Видео: ' + item['video']
				s += '\n' + u'Перевод: ' + item['translate']
				#print s
			except:
				pass

			if s != '':
				li = xbmcgui.ListItem(s)
				li.setProperty('link', link)
				self.list.addItem(li)
			#list.addItem('Item 1\nNew line')
			#list.addItem('Item 2\nNew line')
			#list.addItem('Item 3\nNew line\nAdd line')

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
		print cursel.getLabel()
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
		settings = player.load_settings()
		import urllib
		torr_downloader = TorrentDownloader(urllib.unquote(link), tempPath, settings)
		path = filesystem.join(settings.addon_data_path, torr_downloader.get_subdir_name(), torr_downloader.get_post_index() + '.torrent')
		if not filesystem.exists(path):
			torr_downloader.download()
			path = torr_downloader.get_filename()

		print path
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
		print 'select_file'
		self.has_select_file = True
		self.close()

	def make_choice(self):
		print 'make choice'
		self.has_choice = True
		self.close()

def main():

	print xbmc.getInfoLabel('ListItem.FileName')
	print xbmc.getInfoLabel('ListItem.Path')
	print xbmc.getInfoLabel('ListItem.FileExtension')
	print xbmc.getInfoLabel('ListItem.FileNameAndPath')
	print xbmc.getInfoLabel('ListItem.DBID')		# movie id

	print xbmc.getInfoLabel('Container.FolderPath')

	links = STRMWriterBase.get_links_with_ranks(xbmc.getInfoLabel('ListItem.FileNameAndPath').decode('utf-8'), None)

	window = MyWindow('Media Aggregator', links=links)
	window.doModal()

	#import rpdb2
	#rpdb2.start_embedded_debugger('pw')

	print window.has_choice
	print window.has_select_file

	if not window.has_choice and not window.has_select_file:
		del window
		return

	cursel = window.list.getSelectedItem()
	print cursel.getLabel()
	link = cursel.getProperty('link')

	selected_file = None
	if window.has_select_file:
		#selected_file = window.files.getSelectedItem().getLabel()
		selected_file = window.files.getSelectedItem().getProperty('index')

	del window


	with filesystem.fopen(xbmc.getInfoLabel('ListItem.FileNameAndPath').decode('utf-8'), 'r') as strm:
		src_link = strm.read()
		print src_link
		pattern = 'torrent=(.+?)&'
		match = re.search(pattern, str(link))
		if not match:
			pattern2 = 'torrent=(.+)'
			match = re.search(pattern2, str(link))

		if match:
			dst_link = re.sub(pattern, 'torrent=' + match.group(1) + '&', str(src_link)) + '&onlythis=true'
			print dst_link

			if selected_file:
				#import urllib
				#from tvshowapi import cutStr
				#dst_link += '&cutName=' + urllib.quote(cutStr(selected_file))
				dst_link += '&index=' + str(selected_file)

			xbmc.executebuiltin('xbmc.PlayMedia(' + dst_link + ')')


if __name__ == '__main__':
	main()