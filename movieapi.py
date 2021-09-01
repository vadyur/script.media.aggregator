# -*- coding: utf-8 -*-

from log import debug

import base, filesystem

user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100'

def copy_files(src, dst, pattern):
	from backgrounds import safe_copyfile
	for ext in ['.strm', '.nfo', '.strm.alternative']:
		src_file = filesystem.join(src, base.make_fullpath(pattern, ext))
		if filesystem.exists(src_file):
			dst_file = filesystem.join(dst, base.make_fullpath(pattern, ext))
			safe_copyfile(src_file, dst_file)

def make_imdb_path(path, imdb):
	if imdb and imdb.startswith('tt'):
		return filesystem.join(path, 'TTx' + imdb[3:5], imdb)
	return path

def write_movie(fulltitle, link, settings, parser, path, skip_nfo_exists=False, download_torrent=True):
	debug('+-------------------------------------------')
	filename = parser.make_filename()
	if filename:
		debug('fulltitle: ' + fulltitle.encode('utf-8'))
		debug('filename: ' + filename.encode('utf-8'))
		debug('-------------------------------------------+')

		imdb = parser.get_value('imdb_id')
		new_path = make_imdb_path(path, imdb)

		if new_path != path:
			copy_files(path, new_path, filename)

		with filesystem.save_make_chdir_context(new_path, 'movieaip.write_movie'):
			from strmwriter import STRMWriter
			STRMWriter(parser.link()).write(filename, new_path,
											parser=parser,
											settings=settings)
			from nfowriter import NFOWriter
			NFOWriter(parser, movie_api = parser.movie_api()).write_movie(filename, new_path, skip_nfo_exists=skip_nfo_exists)

			if download_torrent:
				from downloader import TorrentDownloader
				TorrentDownloader(parser.link(), settings.torrents_path(), settings).download()

			settings.update_paths.add(new_path)
			return filesystem.relpath( filesystem.join(new_path, base.make_fullpath(filename, '.strm')), start=settings.base_path())

from vdlib.scrappers.movieapi import get_tmdb_api_key

from vdlib.scrappers.movieapi import IDs

from soup_base import soup_base

from vdlib.scrappers.movieapi import world_art_actors, world_art_info, world_art

from vdlib.scrappers.movieapi import tmdb_movie_item

from vdlib.scrappers.movieapi import KinopoiskAPI, KinopoiskAPI2

from vdlib.scrappers.movieapi import imdb_cast, ImdbAPI

from vdlib.scrappers.movieapi import TMDB_API

from vdlib.scrappers.movieapi import MovieAPI


