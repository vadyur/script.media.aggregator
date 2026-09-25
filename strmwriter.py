# -*- coding: utf-8 -*-

from typing import Optional

from vdlib.util import log
from vdlib.util.log import debug
from vdlib.util import filesystem

from base import *
import os, urllib.parse, sys

class STRMWriter(STRMWriterBase):
	def __init__(self, link: str):
		self.link = link

	def write(self, filename: str, path: str, seasonNumber: Optional[int] = None, episodeNumber: Optional[int] = None,
	          cutname: Optional[str] = None, index: Optional[int] = None, parser = None, settings = None) -> None:

		#------------------------------------------
		# test for settings.update_paths

		if not hasattr(settings, 'update_paths'):
			debug('No update_paths attribute')
		#------------------------------------------

		strmFilename = make_fullpath(filename, '.strm')
		strmFilename = filesystem.join(path, strmFilename)
		
		#------------------------------------------

		link = 'plugin://script.media.aggregator/?action=play&torrent='
		link += urllib.parse.quote(self.link)
		if episodeNumber != None:
			link += '&episodeNumber=' + str(episodeNumber - 1)
		if seasonNumber != None:
			link += '&seasonNumber=' + str(seasonNumber)
		if cutname != None:
			link += '&cutName=' + urllib.parse.quote(cutname)
		if index != None:
			link += '&index=' + str(index)

		#------------------------------------------
		if parser is not None:
			self.make_alternative(strmFilename, link, parser)
			# rank = get_rank(parser.get('full_title', ''), parser, settings),
			# debug('rank: ' + str(rank))
		
			link_with_min_rank = STRMWriterBase.get_link_with_min_rank(strmFilename, settings)
			if not link_with_min_rank is None:
				link = link_with_min_rank
				
		#------------------------------------------
			
		link += '&nfo=' + urllib.parse.quote(make_fullpath(filename, '.nfo'))
		
		#------------------------------------------
		if settings != None:
			path = filesystem.relpath(path, settings.base_path())
			debug(path)
			link += '&path=' + urllib.parse.quote(path)

		#------------------------------------------
		if filesystem.exists(strmFilename):
			with filesystem.fopen(strmFilename, 'r') as f:
				old_link = f.read()
				if old_link == link:
					return
		
		#------------------------------------------
		try:
			with filesystem.fopen(strmFilename, 'w') as f:
				f.write(link)
		except IOError:
			debug('Error write ' + strmFilename)
			return


