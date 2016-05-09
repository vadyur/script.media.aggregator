# coding: utf-8

import log
from log import debug


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
	writer.write(indent + "<" + self.tagName)

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
		writer.write(">%s" % (newl))
		for node in self.childNodes:
			node.writexml(writer, indent + addindent, addindent, newl)
		writer.write("%s</%s>%s" % (indent, self.tagName, newl))
	else:
		writer.write("/>%s" % (newl))


if sys.version_info < (2, 7):
	# replace minidom's function with ours
	xml.dom.minidom.Element.writexml = fixed_writexml


def prettify(xml_text):
	reparsed = minidom.parseString(xml_text)
	return reparsed.toprettyxml(indent=" " * 2, encoding="utf-8")


def write_tree(fn, root):
	try:
		with filesystem.fopen(fn, 'w') as f:
			xml_text = "<?xml version='1.0' encoding='UTF-8'?>\n"
			xml_text += ET.tostring(root).encode('utf-8')
			f.write(prettify(xml_text))
	except IOError as e:
		debug("I/O error({0}): {1}".format(e.errno, e.strerror))
	except TypeError as te:
		debug("Type error({0}): {1}".format(te.errno, te.strerror))


class NFOWriter:
	stripPairs = (
		('<p>', '\n'),
		('<li>', '\n'),
		('<br>', '\n'),
		('<.+?>', ' '),
		('</.+?>', ' '),
		('&nbsp;', ' ',),
		('&laquo;', '"',),
		('&raquo;', '"',),
		('&ndash;', '-'),
	)

	def stripHtml(self, string):
		# from xml.sax.saxutils import unescape
		for (html, replacement) in self.stripPairs:
			string = re.sub(html, replacement, string)

		string = string.replace('&mdash;', u'—')
		string = string.replace('&#151;', u'—')
		return string.strip(' \t\n\r')

	def __init__(self, parser, movie_api=None, tvshow_api=None):
		self.parser = parser
		self.movie_api = movie_api
		self.tvshow_api = tvshow_api

	def add_element_copy(self, parent, tagname, parser):
		value = parser.get_value(tagname)
		if value != '':
			ET.SubElement(parent, tagname).text = unicode(value)
		return value != ''

	def add_element_copy_ep(self, parent, tagname, episode):
		try:
			self.add_element_value(parent, tagname, episode[tagname])
		except:
			pass


	def add_element_value(self, parent, tagname, value):
		if value != '':
			ET.SubElement(parent, tagname).text = unicode(value)
		return value != ''

	def add_element_split(self, parent, tagname, parser):
		values = parser.get_value(tagname).split(',')
		for i in values:
			if i and i != '':
				ET.SubElement(parent, tagname).text = i.strip()
		return len(values) > 0

	def write_episode(self, episode, filename, actors = None):
		root_tag = 'episodedetails'
		root = ET.Element(root_tag)

		self.add_element_copy_ep(root, 'title', episode)
		if self.tvshow_api:
			title = self.tvshow_api.Title()
			if title:
				self.add_element_value(root, 'showtitle', title)

		'''
		self.add_element_value(root, 'season', episode['seasonNumber'])
		self.add_element_value(root, 'episode', episode['episodeNumber'])
		self.add_element_value(root, 'thumb', episode['image'])
		self.add_element_value(root, 'aired', episode['airDate'])
		'''

		for tagname, value in episode.iteritems():
			if tagname != 'title':
				self.add_element_value(root, tagname, value)

		self.add_actors(root)


		#if  self.tvshow_api:
		#	plot = self.tvshow_api.

		'''
		try:
			self.add_element_value(root, 'plot', self.stripHtml(self.movie_api.data()['description']))
		except:
			pass
		'''

		fn = make_fullpath(filename, '.nfo')
		debug(fn)
		write_tree(fn, root)

	def add_actors(self, root):
		kp_id = self.parser.get_value('kp_id')
		if kp_id != '':
			index = 0
			if self.movie_api is not None:
				actors = self.movie_api.Actors()
			else:
				actors = MovieAPI(kinopoisk=kp_id)
			for actorInfo in actors:
				if actorInfo['ru_name'] in self.parser.get_value('actor'):
					actor = ET.SubElement(root, 'actor')
					ET.SubElement(actor, 'name').text = actorInfo['ru_name']
					ET.SubElement(actor, 'role').text = actorInfo['role']
					ET.SubElement(actor, 'order').text = str(index)
					ET.SubElement(actor, 'thumb').text = actorInfo['photo']
					index += 1
		else:
			for name in self.parser.get_value('actor').split(', '):
				if name != '':
					actor = ET.SubElement(root, 'actor')
					ET.SubElement(actor, 'name').text = unicode(name)

	def add_trailer(self, root):
		kp_id = self.parser.get_value('kp_id')
		if kp_id != '':
			trailer = self.movie_api.Trailer()
			if trailer:
				ET.SubElement(root, 'trailer').text = trailer

	def write_title(self, root):
		if self.tvshow_api:
			title = self.tvshow_api.Title()
			if title:
				self.add_element_value(root, 'title', title)
				return

		self.add_element_copy(root, 'title', self.parser)

	def write_originaltitle(self, root):
		self.add_element_copy(root, 'originaltitle', self.parser)

	def write_sorttitle(self, root):
		pass

	def write_set(self, root):
		try:
			debug('Collection: ' + self.movie_api.Collection().encode('utf-8'))
			ET.SubElement(root, 'set').text = self.movie_api.Collection()
		except:
			pass

	def write_rating(self, root):
		if self.parser.get('rating', None):
			ET.SubElement(root, 'rating').text = str(self.parser.get_value('rating'))
			return

		try:
			debug(self.movie_api.imdbRating())
			ET.SubElement(root, 'rating').text = str(self.movie_api.imdbRating())
		except:
			pass

	def write_year(self, root):
		self.add_element_copy(root, 'year', self.parser)

	def write_top250(self, root):
		pass

	def write_votes(self, root):
		pass

	def write_outline(self, root):
		pass

	def write_plot(self, root):
		plot = self.stripHtml(self.parser.get_value('plot'))
		'''
		if plot == '' and self.tvshow_api is not None:
			try:
				plot = self.stripHtml(self.tvshow_api.data()['description'])
			except:
				pass
		'''
		self.add_element_value(root, 'plot', plot)

	def write_tagline(self, root):
		pass

	def write_runtime(self, root):
		try:
			debug(self.movie_api.Runtime())
			ET.SubElement(root, 'runtime').text = str(self.movie_api.Runtime())
		except:
			pass

	def write_thumb(self, root):
		thumbs = []
		try:
			thumbs.append({'preview': 'http://image.tmdb.org/t/p/w500' + self.movie_api[u'poster_path'],
						   'original': u'http://image.tmdb.org/t/p/original' + self.movie_api[u'poster_path']})
		except:
			pass

		if self.movie_api is not None:
			try:
				poster = self.movie_api.Poster()
				if poster != '':
					thumbs.append({'original': poster})
			except:
				pass

		if self.tvshow_api is not None:
			for poster in self.tvshow_api.Poster():
				thumbs.append({	'preview': poster['thumb'],
								'original': poster['path']})

		tn = self.parser.get_value('thumbnail')
		if tn != '':
			thumbs.append({'original': tn})

		for item in thumbs:
			if 'preview' in item:
				thumb = ET.SubElement(root, "thumb", aspect='poster', preview=item['preview'])
			else:
				thumb = ET.SubElement(root, "thumb", aspect='poster')
			thumb.text = item['original']


	def write_fanart(self, root):
		fanarts = []
		try:
			fanarts.append(u'http://image.tmdb.org/t/p/original' + self.movie_api[u'backdrop_path'])
		except:
			pass

		if self.tvshow_api is not None:
			for fa in self.tvshow_api.Fanart():
				fanarts.append(fa['path'])

		if len(fanarts) > 0:
			fanart = ET.SubElement(root, 'fanart')
			for fa in fanarts:
				ET.SubElement(fanart, 'thumb').text = fa


	def write_mpaa(self, root):
		try:
			debug('Rated: ' + self.movie_api.Rated())
			ET.SubElement(root, 'mpaa').text = str(self.movie_api.Rated())
		except:
			pass

	def write_playcount(self, root):
		pass

	def write_id(self, root):
		imdb_id = self.parser.get_value('imdb_id')
		ET.SubElement(root, 'id').text = imdb_id

	def write_filenameandpath(self, root):
		pass

	def write_trailer(self, root):
		self.add_trailer(root)

	def write_genre(self, root):
		self.add_element_split(root, 'genre', self.parser)

	def write_tag(self, root):
		tags = self.parser.get('tag', None)
		if isinstance(tags, list):
			for tag in tags:
				self.add_element_value(root, 'tag', tag)

	def write_credits(self, root):
		pass

	def write_director(self, root):
		self.add_element_split(root, 'director', self.parser)

	def write_actor(self, root):
		self.add_actors(root)

	def write_country(self, root):
		self.add_element_split(root, 'country', self.parser)

	def write_studio(self, root):
		self.add_element_split(root, 'studio', self.parser)

	def write_movie(self, filename):
		root = ET.Element('movie')
		self.write_title(root)
		self.write_originaltitle(root)
		self.write_sorttitle(root)
		self.write_set(root)
		self.write_rating(root)
		self.write_year(root)
		self.write_top250(root)
		self.write_votes(root)
		self.write_outline(root)
		self.write_plot(root)
		self.write_tagline(root)
		self.write_runtime(root)
		self.write_thumb(root)
		self.write_fanart(root)
		self.write_mpaa(root)
		self.write_playcount(root)
		self.write_id(root)
		self.write_filenameandpath(root)
		self.write_trailer(root)
		self.write_genre(root)
		self.write_tag(root)
		self.write_country(root)
		self.write_credits(root)
		self.write_director(root)
		self.write_studio(root)
		self.write_actor(root)
		fn = make_fullpath(filename, '.nfo')
		debug(fn)
		write_tree(fn, root)

	def write_tvshow_nfo(self):
		root = ET.Element('tvshow')
		self.write_title(root)
		self.write_originaltitle(root)
		self.write_sorttitle(root)
		self.write_set(root)
		self.write_rating(root)
		self.write_year(root)
		self.write_top250(root)
		self.write_votes(root)
		self.write_outline(root)
		self.write_plot(root)
		self.write_tagline(root)
		self.write_runtime(root)
		self.write_thumb(root)
		self.write_fanart(root)
		self.write_mpaa(root)
		self.write_playcount(root)
		self.write_id(root)
		self.write_filenameandpath(root)
		self.write_trailer(root)
		self.write_genre(root)
		self.write_tag(root)
		self.write_country(root)
		self.write_credits(root)
		self.write_director(root)
		self.write_studio(root)
		self.write_actor(root)
		fn = make_fullpath('tvshow', '.nfo')
		debug(fn)
		write_tree(fn, root)
