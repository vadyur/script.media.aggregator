# coding: utf-8

import sys
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from xml.dom.minidom import *
from base import *
from tvshowapi import *
from movieapi import *

def fixed_writexml(self, writer, indent="", addindent="", newl=""):
	# indent = current indentation
	# addindent = indentation to add to higher levels
	# newl = newline string
	writer.write(indent+"<" + self.tagName)

	attrs = self._get_attributes()
	a_names = attrs.keys()
	a_names.sort()

	for a_name in a_names:
		writer.write(" %s=\"" % a_name)
		xml.dom.minidom._write_data(writer, attrs[a_name].value)
		writer.write("\"")
	if self.childNodes:
		if len(self.childNodes) == 1 \
		  and self.childNodes[0].nodeType == xml.dom.minidom.Node.TEXT_NODE:
			writer.write(">")
			self.childNodes[0].writexml(writer, "", "", "")
			writer.write("</%s>%s" % (self.tagName, newl))
			return
		writer.write(">%s"%(newl))
		for node in self.childNodes:
			node.writexml(writer,indent+addindent,addindent,newl)
		writer.write("%s</%s>%s" % (indent,self.tagName,newl))
	else:
		writer.write("/>%s"%(newl))
		
if sys.version_info < (2, 7):		
	# replace minidom's function with ours
	xml.dom.minidom.Element.writexml = fixed_writexml

def prettify(xml_text):
    reparsed = minidom.parseString(xml_text)
    return reparsed.toprettyxml(indent=" "*2, encoding="utf-8")

def write_tree(fn, root):
	try:
		with filesystem.fopen(fn, 'w') as f:
			xml_text = "<?xml version='1.0' encoding='UTF-8'?>\n"
			xml_text += ET.tostring(root).encode('utf-8')
			f.write(prettify(xml_text))
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)


class NFOWriter:

	stripPairs = (
		('<p>', '\n'),
		('<li>', '\n'),
		('<br>', '\n'),
		('<.+?>', ' '),
		('</.+?>', ' '),
		( '&nbsp;', ' ',),
		('&laquo;', '"',),
		('&raquo;', '"', ),
		('&ndash;', '-'),
	)

	def stripHtml(self, string):
		# from xml.sax.saxutils import unescape
		for (html, replacement) in self.stripPairs:
			string = re.sub(html, replacement, string)

		string = string.replace('&mdash;', u'—')
		string = string.replace('&#151;', u'—')
		return string.strip(' \t\n\r')

	def add_element_copy(self, parent, tagname, parser):
		value = parser.get_value(tagname)
		if value != '':
			ET.SubElement(parent, tagname).text = unicode(value)
		return value

	def add_element_value(self, parent, tagname, value):
		if value != '':
			ET.SubElement(parent, tagname).text = unicode(value)
		
	def add_element_split(self, parent, tagname, parser):
		for i in parser.get_value(tagname).split(','):
			ET.SubElement(parent, tagname).text = i.strip()
			
	def make_tvshow_info(self, parent, tvshow_api, desc_parser):
		if tvshow_api==None:
			return
		if not tvshow_api.valid():
			return

		# add poster
		if 'image' in tvshow_api.data():
			self.add_element_value(parent, "thumb", tvshow_api.data()['image']);
			
		self.add_element_copy(parent, 'rating', desc_parser)

		# add fanart
		fanart = ET.SubElement(parent, 'fanart')
		if desc_parser.fanart() is not None:
			for item in desc_parser.fanart():
				self.add_element_value(fanart, "thumb", item)
		
	def make_imdbid_info(self, parent, movie_api, tn):
		try:
			try:
				thumb = ET.SubElement(parent, "thumb", aspect='poster', preview='http://image.tmdb.org/t/p/w500' + movie_api[u'poster_path'])
				thumb.text = u'http://image.tmdb.org/t/p/original' + movie_api[u'poster_path']

				if tn != '':
					ET.SubElement(parent, "thumb", aspect='poster', preview=tn).text = tn
			except:
				try:
					poster = movie_api.Poster()
					if poster != '':
						ET.SubElement(parent, "thumb", aspect='poster', preview=poster).text = poster
				except:
					pass

			try:
				fanart = ET.SubElement(parent, 'fanart')
				thumb = ET.SubElement(fanart, "thumb", preview='http://image.tmdb.org/t/p/w780' + movie_api[u'backdrop_path'])
				thumb.text = u'http://image.tmdb.org/t/p/original' + movie_api[u'backdrop_path']
			except:
				pass
			
			print movie_api.imdbRating()
			ET.SubElement(parent, 'rating').text = movie_api.imdbRating()
			print movie_api.Runtime()
			ET.SubElement(parent, 'runtime').text = movie_api.Runtime()
			print 'Rated: ' + movie_api.Rated()
			ET.SubElement(parent, 'mpaa').text = movie_api.Rated()
			print 'Collection: ' + movie_api.Collection().encode('utf-8')
			ET.SubElement(parent, 'set').text = movie_api.Collection()
			
			for tag in movie_api.Tags():
				ET.SubElement(parent, 'tag').text = tag
				print 'tag: ' + tag.encode('utf-8')
			
		except:
			return False
			
		return True
		
	def write_episode(self, episode, filename, tvshow_api=None):
		root_tag='episodedetails'
		root = ET.Element(root_tag)
		
		self.add_element_value(root, 'title', episode['title'])
		self.add_element_value(root, 'season', episode['seasonNumber'])
		self.add_element_value(root, 'episode', episode['episodeNumber'])
		self.add_element_value(root, 'thumb', episode['image'])
		self.add_element_value(root, 'aired', episode['airDate'])

		try:
			self.add_element_value(root, 'plot', self.stripHtml(tvshow_api.data()['description']))
		except:
			pass
		
		fn = make_fullpath(filename, '.nfo')
		write_tree(fn, root)
		
	def add_actors(self, root, desc_parser):
		kp_id = desc_parser.get_value('kp_id')
		if kp_id != '':
			movie_api = desc_parser.movie_api()
			index = 0
			for actorInfo in movie_api.Actors():
				if actorInfo['ru_name'] in desc_parser.get_value('actor'):
					actor = ET.SubElement(root, 'actor')
					ET.SubElement(actor, 'name').text = actorInfo['ru_name']
					ET.SubElement(actor, 'role').text = actorInfo['role']
					ET.SubElement(actor, 'order').text = str(index)
					ET.SubElement(actor, 'thumb').text = actorInfo['photo']
					index += 1
		else:
			for name in desc_parser.get_value('actor').split(', '):
				actor = ET.SubElement(root, 'actor')
				ET.SubElement(actor, 'name').text = name
				
	def add_trailer(self, root, desc_parser):
		kp_id = desc_parser.get_value('kp_id')
		if kp_id != '':
			movie_api = desc_parser.movie_api()
			trailer = movie_api.Trailer()
			if trailer:
				ET.SubElement(root, 'trailer').text = trailer
		
	def write(self, desc_parser, filename, root_tag='movie', tvshow_api=None):
		root = ET.Element(root_tag)
		
		self.add_element_copy(root, 'title', desc_parser)
		self.add_element_copy(root, 'originaltitle', desc_parser)
		self.add_element_copy(root, 'year', desc_parser)
		self.add_element_split(root, 'director', desc_parser)

		plot = self.stripHtml(desc_parser.get_value('plot'))
		if plot == '' and tvshow_api is not None:
			try:
				plot = self.stripHtml(tvshow_api.data()['description'])
			except:
				pass
		self.add_element_value(root, 'plot', plot)
		imdb_id = desc_parser.get_value('imdb_id')
		ET.SubElement(root, 'id').text = imdb_id
		self.add_element_split(root, 'genre', desc_parser)
		self.add_element_split(root, 'country', desc_parser)
		self.add_element_split(root, 'studio', desc_parser)
		
		self.add_actors(root, desc_parser)
		self.add_trailer(root, desc_parser)
			
		tn = desc_parser.get_value('thumbnail')
		if imdb_id != '':
			movie_api = desc_parser.movie_api()
			if self.make_imdbid_info(root, movie_api, tn):
				tn = ''
				
		if root_tag=='tvshow':
			self.make_tvshow_info(root, tvshow_api, desc_parser)
				
		if tn != '':
			thumb = ET.SubElement(root, "thumb", aspect='poster', preview=tn)
			thumb.text = tn
			
		if desc_parser.get_value('gold'):
			ET.SubElement(root, 'gold')
			
		fn = make_fullpath(filename, '.nfo')
		write_tree(fn, root)
	
