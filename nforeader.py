# -*- coding: utf-8 -*-

import log
from log import debug


import os
import xml.etree.ElementTree as ET
import filesystem

def ensure_utf8(string):
	if isinstance(string, unicode):
		string = string.encode('utf-8')
	return string

class NFOReader(object):
	def __init__(self, path, temp_path):
		self.__root = None
		self.__path = path
		self.__temp_path = temp_path
		
		if not filesystem.exists(path):
			return

		try:
			with filesystem.fopen(path, 'r') as f:
				content = f.read()
				try:
					i = content.index('</movie>')
					if i >= 0:
						content = content[0:i + len('</movie>')]
				except:
					pass
				self.__root = ET.fromstring(content)  #ET.parse(self.__path)
		except IOError as e:
			debug("NFOReader: I/O error({0}): {1}".format(e.errno, e.strerror))

	@property
	def path(self):
		return self.__path
		
	@staticmethod
	def make_path(base_path, rel_path, filename):
		# params is utf-8
		path = filesystem.join(base_path.decode('utf-8'), rel_path.decode('utf-8'), filename.decode('utf-8'))

		if path.startswith('/') or '://' in path:
			path = path.replace('\\', '/')
		elif len(path) > 2 and path[1] == ':' and path[2] == '\\':
			path = path.replace('/', '\\')

		return path

	def is_episode(self):
		return self.__root.tag == 'episodedetails'

	def imdb_id(self):
		root = self.__root

		imdb = root.find('id')
		if imdb is not None and imdb.text.startswith('tt'):
			return imdb.text

		return None
		
	def get_info(self):
		
		root = self.__root

		info = {}
		if root == None:
			return info
		
		string_items = ['genre', 'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle', 'duration',
						'studio', 'code', 'aired', 'credits', 'album', 'votes', 'trailer', 'thumb']
		integer_items = ['year', 'episode', 'season', 'top250', 'tracknumber']
		
		float_items = ['rating']
		
		cast = []
		castandrole = []
		for child in root:
			try:
				#debug(child.tag, child.text)
				if child.tag in string_items and child.text:
					info[child.tag] = ensure_utf8(child.text)
				if child.tag in integer_items and child.text:
					info[child.tag] = int(child.text)
				if child.tag in float_items and child.text:
					info[child.tag] = float(child.text)
				if 'actor' in child.tag:
					for item in child:
						name = ''
						role = ''
						if 'name' in item.tag:
							name = ensure_utf8( item.text )
						if 'role' in item.tag:
							role = ensure_utf8( item.text )
						cast.append(name)
						castandrole.append((name, role))
			except:
				pass
					
		if len(cast) > 0:
			info['cast'] = cast
		if len(castandrole) > 0:
			info['castandrole'] = castandrole

		if not info.get('plotoutline'):
			info['plotoutline'] = info.get('plot', '')
				
		debug(info)
		return info
		
	def download_image(self, url, type):
		import requests
		r = requests.get(url)
		debug(r.headers)
		
		if r.headers[ 'Content-Type'] == 'image/jpeg':
			filename = filesystem.join(self.__temp_path, 'temp.media-aggregator.' + type + '.jpg')
			
			debug('Start download: ' + filename + ' from ' + url)
			
			with filesystem.fopen(filename, 'wb') as f:
				for chunk in r.iter_content(100000):
					f.write(chunk)
					
			debug('End download: ' + filename)
			return filename
				
		return None
		
		
	def get_art(self):
		root = self.__root
		art = {}
		
		for child in root:
			if child.tag == 'thumb':
				path = child.text #self.download_image(child.text, 'poster-thumb')
				if path != None:
					art['thumb'] = path
					art['poster'] = path
					art['thumbnailImage'] = path

			
			if child.tag == 'fanart':
				fanart = child
				for thumb in fanart:
					if thumb.tag == 'thumb':
						art['fanart'] = thumb.text
						
		debug(art)
		return art

	def tvs_reader(self):
		is_episode = self.is_episode()

		if is_episode:
			path = filesystem.dirname(self.path)
			path = filesystem.abspath(filesystem.join(path, os.pardir))
			path = filesystem.join(path, u'tvshow.nfo')

			if filesystem.exists(path):
				debug(u'tvs_reader: ' + path)
				return NFOReader(path, self.__temp_path)

		return None

	def try_join_tvshow_info(self):
		info = self.get_info()
		tvs_reader = self.tvs_reader()
		if tvs_reader:
			tvs_info = tvs_reader.get_info()
			info = dict(tvs_info, **info)

			debug(info)

		return info


	def try_join_tvshow_art(self):
		art = self.get_art()
		tvs_reader = self.tvs_reader()
		if tvs_reader:
			tvs_art = tvs_reader.get_art()
			art = dict(tvs_art, **art)

			debug(art)

		return art

	def make_list_item(self, playable_url):
		import xbmcgui
		list_item = xbmcgui.ListItem(path=playable_url)
		list_item.setInfo('video', self.try_join_tvshow_info())

		art = self.try_join_tvshow_art()
		list_item.setThumbnailImage(art.get('poster', ''))
		
		return list_item


# tests
if __name__ == '__main__':
	#reader = NFOReader(u'd:\\-=Vd=-\\Videos\\TVShows\\Однажды в сказке\\Season 1\\03. episode_s01e03.nfo', None)
	#print reader.try_join_tvshow_info()
	#print reader.try_join_tvshow_art()

	rd = NFOReader(u'C:\\Users\\vd\\Videos\\TVShows\\Гастролёры\\Season 1\\03. episode_s01e03.nfo', '')
	tvs_rd = rd.tvs_reader()
	imdb_id = tvs_rd.imdb_id()




