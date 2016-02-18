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


		'''
		# Создаем кнопку.
		button = pyxbmct.Button('Close')
		# Помещаем кнопку в сетку.
		self.placeControl(button, 1, 1)
		# Устанавливаем начальный фокус на кнопку.
		self.setFocus(button)
		# Связываем кнопку с методом.
		self.connect(button, self.close)
		'''
		# Связываем клавиатурное действие с методом.
		self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
		self.has_choice = False

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
	if not window.has_choice:
		del window
		return

	cursel = window.list.getSelectedItem()
	print cursel.getLabel()
	link = cursel.getProperty('link')
	del window


#	import rpdb2
#	rpdb2.start_embedded_debugger('pw')
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
			xbmc.executebuiltin('xbmc.PlayMedia(' + dst_link + ')')


if __name__ == '__main__':
	main()