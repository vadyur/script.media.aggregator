import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from base import *
from tvshowapi import *
from movieapi import *

def prettify(xml_text):
    reparsed = minidom.parseString(xml_text)
    return reparsed.toprettyxml(indent="\t", encoding="utf-8")

def write_tree(fn, root):
	try:
		with open(fn, 'w') as f:
			xml_text = "<?xml version='1.0' encoding='UTF-8'?>\n"
			xml_text += ET.tostring(root).encode('utf-8')
			f.write(prettify(xml_text))
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)		
	

class NFOWriter:
	def add_element_copy(self, parent, tagname, parser):
		value = parser.get_value(tagname)
		if value != '':
			ET.SubElement(parent, tagname).text = unicode(value)
		return value

	def add_element_value(self, parent, tagname, value):
		if value != '':
			ET.SubElement(parent, tagname).text = unicode(value)
		
	def add_element_split(self, parent, tagname, parser):
		for i in parser.get_value(tagname).split(', '):
			ET.SubElement(parent, tagname).text = i
			
	def make_tvshow_info(self, parent, tvshow_api, desc_parser):
		if tvshow_api==None:
			return
		if not tvshow_api.valid():
			return
			
		self.add_element_copy(parent, 'rating', desc_parser)
		
	def make_imdbid_info(self, parent, movie_api):
		try:
			tmdb_id = movie_api[u'id']
			thumb = ET.SubElement(parent, "thumb", aspect='poster', preview='http://image.tmdb.org/t/p/w500' + movie_api[u'poster_path'])
			thumb.text = u'http://image.tmdb.org/t/p/original' + movie_api[u'poster_path']
			
			fanart = ET.SubElement(parent, 'fanart')
			thumb = ET.SubElement(fanart, "thumb", preview='http://image.tmdb.org/t/p/w780' + movie_api[u'backdrop_path'])
			thumb.text = u'http://image.tmdb.org/t/p/original' + movie_api[u'backdrop_path']
			
			print movie_api.imdbRating()
			ET.SubElement(parent, 'rating').text = movie_api.imdbRating()
			print movie_api.Runtime()
			ET.SubElement(parent, 'runtime').text = movie_api.Runtime()
			print 'Rated: ' + movie_api.Rated()
			ET.SubElement(parent, 'mpaa').text = movie_api.Rated()
			print 'Collection: ' + movie_api.Collection().encode('utf-8')
			ET.SubElement(parent, 'set').text = movie_api.Collection()
		except:
			pass
		
	def write_episode(self, episode, filename, tvshow_api=None):
		root_tag='episodedetails'
		root = ET.Element(root_tag)
		
		self.add_element_value(root, 'title', episode['title'])
		self.add_element_value(root, 'season', episode['seasonNumber'])
		self.add_element_value(root, 'episode', episode['episodeNumber'])
		self.add_element_value(root, 'thumb', episode['image'])
		self.add_element_value(root, 'aired', episode['airDate'])

		try:
			self.add_element_value(root, 'plot', tvshow_api.data()['description'])
		except:
			pass
		
		fn = make_fullpath(filename, '.nfo')
		write_tree(fn, root)
		
	def write(self, desc_parser, filename, root_tag='movie', tvshow_api=None):
		root = ET.Element(root_tag)
		
		self.add_element_copy(root, 'title', desc_parser)
		self.add_element_copy(root, 'originaltitle', desc_parser)
		self.add_element_copy(root, 'year', desc_parser)
		self.add_element_split(root, 'director', desc_parser)
		self.add_element_copy(root, 'plot', desc_parser)
		imdb_id = desc_parser.get_value('imdb_id')
		ET.SubElement(root, 'id').text = imdb_id
		self.add_element_split(root, 'genre', desc_parser)
		self.add_element_split(root, 'country', desc_parser)
		self.add_element_split(root, 'studio', desc_parser)
			
		tmdb_id = ''
		if imdb_id != '':
			movie_api = MovieAPI(imdb_id)
			self.make_imdbid_info(root, movie_api) 
		elif root_tag=='tvshow':
			self.make_tvshow_info(root, tvshow_api, desc_parser)
				
		tn = desc_parser.get_value('thumbnail')
		if tn != '':
			thumb = ET.SubElement(root, "thumb", aspect='poster', preview=tn)
			thumb.text = tn
			
		if desc_parser.get_value('gold'):
			ET.SubElement(root, 'gold')
			
		fn = make_fullpath(filename, '.nfo')
		write_tree(fn, root)
	
		'''
		if tmdb_id != '':
			with open(fn, "a") as myfile:
				myfile.write('\n' + 'http://www.themoviedb.org/movie/' + str(tmdb_id))
		elif imdb_id != '':
			with open(fn, "a") as myfile:
				myfile.write('\n' + 'http://www.imdb.com/title/' + imdb_id + '/')
		'''