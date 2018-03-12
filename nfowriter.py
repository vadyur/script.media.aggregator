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

	def __init__(self, parser, movie_api=EmptyMovieApi(), tvshow_api=None):
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

	def write_episode(self, episode, filename, path, actors = None, skip_nfo_exists=False):
		fn = make_fullpath(filename, '.nfo')
		fn = filesystem.join(path, fn)

		debug(fn)
		if skip_nfo_exists and filesystem.exists(fn):
			return

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

		write_tree(fn, root)

	def add_actors(self, root):
		index = 0
		actors = []
		try:
			actors = self.movie_api.actors()
		except:
			pass
		#if not actors and self.tvshow_api is not None:
		#	actors = self.tvshow_api.Actors()

		if actors:
			for actorInfo in actors:
				if 'ru_name' in actorInfo:
					actor = ET.SubElement(root, 'actor')

					def setup(dst_name, src_name):
						try:
							ET.SubElement(actor, dst_name).text = actorInfo[src_name]
						except: pass

					setup('name','ru_name')
					setup('role','role')
					ET.SubElement(actor, 'order').text = str(index)
					setup('thumb', 'photo')
					index += 1
		else:
			for name in self.parser.get_value('actor').split(', '):
				if name != '':
					actor = ET.SubElement(root, 'actor')
					ET.SubElement(actor, 'name').text = unicode(name)

	def add_trailer(self, root):
		try:
			trailer = self.movie_api['trailer']
			ET.SubElement(root, 'trailer').text = trailer
		except AttributeError:
			pass

	def write_title(self, root):
		title = self.movie_api.get('title')
		if not title and self.tvshow_api:
			title = self.tvshow_api.Title()
		if title:
			self.add_element_value(root, 'title', title)
		else:
			self.add_element_copy(root, 'title', self.parser)

	def write_originaltitle(self, root):
		originaltitle = self.movie_api.get('originaltitle')
		if originaltitle:
			self.add_element_value(root, 'originaltitle', originaltitle)
		else:
			self.add_element_copy(root, 'originaltitle', self.parser)

	def write_sorttitle(self, root):
		pass

	def write_set(self, root):
		try:
			res = self.movie_api['set']
			debug(u'Collection: ' + res)
			ET.SubElement(root, 'set').text = res
		except:
			pass

	def write_rating(self, root):
		try:
			res = self.movie_api['rating']
			ET.SubElement(root, 'rating').text = str(res)
			return
		except:
			pass

		if self.parser.get('rating', None):
			ET.SubElement(root, 'rating').text = str(self.parser.get_value('rating'))


	def write_year(self, root):
		year = self.movie_api.get('year')
		if not year and self.tvshow_api:
			year = self.tvshow_api.Year()
		if year:
			ET.SubElement(root, 'year').text = str(year)
		else:
			self.add_element_copy(root, 'year', self.parser)

	def write_top250(self, root):
		pass

	def write_votes(self, root):
		pass

	def write_outline(self, root):
		pass

	def write_plot(self, root):
		plot = None
		try:
			plot = self.movie_api.ru('plot')
		except AttributeError:
			pass

		if not plot:
			plot = self.stripHtml(self.parser.get_value('plot'))

		if plot:
			self.add_element_value(root, 'plot', plot)

	def write_tagline(self, root):
		pass

	def write_runtime(self, root):
		try:
			rt = self.movie_api['runtime']
			debug(rt)
			ET.SubElement(root, 'runtime').text = str(rt)
		except:
			pass

	def write_thumb(self, root):
		thumbs = []
		try:
			poster = self.movie_api['poster']
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
			fanarts.append( self.movie_api['fanart'] )
		except:
			pass

		if self.tvshow_api is not None:
			for fa in self.tvshow_api.Fanart():
				fanarts.append(fa['path'])

		if 'fanart' in self.parser.Dict():
			for fa in self.parser.get('fanart', []):
				fanarts.append(fa)

		if len(fanarts) > 0:
			fanart = ET.SubElement(root, 'fanart')
			for fa in fanarts:
				ET.SubElement(fanart, 'thumb').text = fa


	def write_mpaa(self, root):
		try:
			mpaa = self.movie_api['mpaa']
			ET.SubElement(root, 'mpaa').text = str(mpaa)
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
		#self.add_element_split(root, 'genre', self.parser)

		try:
			genres = self.movie_api['genres']
		except:
			s = self.parser.get_value('genre')
			from base import lower

			if ',' in s:
				genres = lower(s).split(',')
			elif ' ' in s:
				genres = lower(s).split(' ')
			else:
				genres = [lower(s)]

		for i in genres:
			if i:
				ET.SubElement(root, 'genre').text = i.strip()
		return len(genres) > 0


	def write_tag(self, root):
		tags = self.parser.get('tag', None)
		if isinstance(tags, list):
			for tag in tags:
				self.add_element_value(root, 'tag', tag)

	def write_credits(self, root):
		pass

	def write_director(self, root):
		try:
			director = self.movie_api.ru('director')
			for d in director:
				self.add_element_value(root, 'director', d)
		except:
			self.add_element_split(root, 'director', self.parser)

	def write_actor(self, root):
		self.add_actors(root)

	def write_country(self, root):
		try:
			cc = self.movie_api['countries']
			for c in cc:
				self.add_element_value(root, 'country', c)
		except:
			self.add_element_split(root, 'country', self.parser)

	def write_studio(self, root):
		try:
			ss = self.movie_api['studios']
			for s in ss:
				self.add_element_value(root, 'studio', s)
		except:
			self.add_element_split(root, 'studio', self.parser)

	def write_premiered(self, root):
		if self.tvshow_api:
			val = self.tvshow_api.Premiered()
			if val:
				self.add_element_value(root, 'premiered', val)


	def write_movie(self, filename, path, skip_nfo_exists=False):
		fn = make_fullpath(filename, '.nfo')
		fn = filesystem.join(path, fn)
		debug(fn)
		if skip_nfo_exists and filesystem.exists(fn):
			return

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
		write_tree(fn, root)

	def write_tvshow_nfo(self, tvshow_path, skip_nfo_exists=False):
		tvshow_nfo_path = make_fullpath('tvshow', '.nfo')
		tvshow_nfo_path = filesystem.join(tvshow_path, tvshow_nfo_path)
		
		debug(tvshow_nfo_path)
		if skip_nfo_exists and filesystem.exists(tvshow_nfo_path):
			return

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
		self.write_premiered(root)
		self.write_studio(root)
		self.write_actor(root)
		write_tree(tvshow_nfo_path, root)
