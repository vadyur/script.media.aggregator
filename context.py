# -*- coding: utf-8 -*-

import sys, xbmc, re, xbmcgui

import pyxbmct.addonwindow as pyxbmct

from base import STRMWriterBase


class MyWindow(pyxbmct.AddonDialogWindow):
	def __init__(self, title='', links = []):
		# Вызываем конструктор базового класса.
		super(MyWindow, self).__init__(title)
		# Устанавливаем ширину и высоту окна, а также разрешение сетки (Grid):
		# 2 строки и 3 столбца.
		self.setGeometry(850, 550, 1, 1)

		'''
		# Создаем текстовую надпись.
		label = pyxbmct.Label('This is a PyXBMCt window.', alignment=pyxbmct.ALIGN_CENTER)
		# Помещаем надпись в сетку.
		self.placeControl(label, 0, 0, columnspan=3)
		'''

		list = pyxbmct.List('font14', _itemHeight=80)
		self.placeControl(list, 0, 0)
		self.setFocus(list)

		for item in links:
			try:
				s = ''
				s += item['full_title']
				s += '\n' + u'Видео: ' + item['video']
				s += '\n' + u'Перевод: ' + item['translate']
				#print s
			except:
				pass

			if s != '':
				list.addItem(s)
			#list.addItem('Item 1\nNew line')
			#list.addItem('Item 2\nNew line')
			#list.addItem('Item 3\nNew line\nAdd line')

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

def main():

	print xbmc.getInfoLabel('ListItem.FileName')
	print xbmc.getInfoLabel('ListItem.Path')
	print xbmc.getInfoLabel('ListItem.FileExtension')
	print xbmc.getInfoLabel('ListItem.FileNameAndPath')
	print xbmc.getInfoLabel('ListItem.DBID')		# movie id

	print xbmc.getInfoLabel('Container.FolderPath')

	# import rpdb2
	# rpdb2.start_embedded_debugger('pw')


	links = STRMWriterBase.get_links_with_ranks(xbmc.getInfoLabel('ListItem.FileNameAndPath').decode('utf-8'), None)

	window = MyWindow('Media Aggregator', links=links)
	window.doModal()
	del window


if __name__ == '__main__':
	main()