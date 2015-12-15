# -*- coding: utf-8 -*-

from base import *
import os, urllib2, sys, filesystem

class STRMWriter(STRMWriterBase):
	def __init__(self, link):
		self.link = link
		
	def write(self, filename, episodeNumber = None, rank = 0, settings = None):
		fname = make_fullpath(filename, '.strm')
		
		#------------------------------------------

		link = u'plugin://script.media.aggregator/?action=play&torrent='
		link += urllib2.quote(self.link.encode('utf-8'))
		if episodeNumber != None:
			link += u'&episodeNumber=' + str(episodeNumber - 1)

		#------------------------------------------
		if rank != 0:
			self.make_alternative(fname, link, rank)
			print 'rank: ' + str(rank)
		
			link_with_min_rank = self.get_link_with_min_rank(fname)
			if len(link_with_min_rank) > 0:
				link = link_with_min_rank
				
		#------------------------------------------
			
		link += u'&nfo=' + urllib2.quote(make_fullpath(filename, '.nfo').encode('utf-8'))
		
		#------------------------------------------
		if settings != None:
			path = filesystem.relpath(filesystem.getcwd(), settings.base_path())
			path = unicode(path, filesystem.get_filesystem_encoding())
			print path.encode('utf-8')
			link += u'&path=' + urllib2.quote(path.encode('utf-8'))

		#------------------------------------------
		if filesystem.exists(fname):
			with open(fname, 'r') as f:
				old_link = f.read()
				if old_link.decode('utf-8') == link:
					return
		
		#------------------------------------------
		with open(fname, 'w') as f:
			f.write(link.encode('utf-8'))


