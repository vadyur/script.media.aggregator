import os, xbmcgui
import xml.etree.ElementTree as ET
import requests

class NFOReader(object):
	def __init__(self, path, temp_path):
		self.__path = path
		self.__temp_path = temp_path
		
		with open(path, 'r') as f:
			content = f.read()
			try:
				i = content.index('</movie>')
				if i >= 0:
					content = content[0:i + len('</movie>')]
			except:
				pass
			self.__root = ET.fromstring(content)  #ET.parse(self.__path)
		
	@staticmethod
	def make_path(base_path, rel_path, filename):
		# params is utf-8
		path = os.path.join(base_path.decode('utf-8'), rel_path.decode('utf-8'), filename.decode('utf-8'))
		return path
		
	def get_info(self):
		
		root = self.__root
		
		string_items = ['genre', 'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle', 'duration',
						'studio', 'code', 'aired', 'credits', 'album', 'votes', 'trailer', 'thumb']
		integer_items = ['year', 'episode', 'season', 'top250', 'tracknumber']
		
		float_items = ['rating']
		
		info = {}

		for child in root:
			#print child.tag, child.text
			if child.tag in string_items:
				info[child.tag] = child.text
			if child.tag in integer_items:
				info[child.tag] = int(child.text)
			if child.tag in float_items:
				info[child.tag] = float(child.text)
				
		print info
		return info
		
	def download_image(self, url, type):
		r = requests.get(url)
		print r.headers
		
		if r.headers[ 'Content-Type'] == 'image/jpeg':
			filename = os.path.join(self.__temp_path, 'temp.anidub.media-aggregator.' + type + '.jpg')
			
			print 'Start download: ' + filename + ' from ' + url
			
			with open(filename, 'wb') as f:
				for chunk in r.iter_content(100000):
					f.write(chunk)
					
			print 'End download: ' + filename
			return filename
				
		return None
		
		
	def get_art(self):
		root = self.__root
		art = {}
		
		for child in root:
			if child.tag == 'thumb':
				path = self.download_image(child.text, 'poster-thumb')
				if path != None:
					art['thumb'] = path
					art['poster'] = path

			
			if child.tag == 'fanart':
				fanart = child
				for thumb in fanart:
					if thumb.tag == 'thumb':
						art['fanart'] = thumb.text
						
		print art
		return art
				
	def make_list_item(self, playable_url):
		#item = self.get_art()
		list_item = xbmcgui.ListItem(path=playable_url)
		list_item.setInfo('video', self.get_info())
		#list_item.setArt(item)
		
		return list_item
