# -*- coding: utf-8 -*-

import filesystem, log
from movieapi import MovieAPI

def addon_data_path():
	from player import _addon, _addondir
	if _addon.getSetting('data_path'):
		return _addon.getSetting('data_path')
	else:
		return _addondir

def recheck_torrent_if_need(from_time, settings):
	if settings.torrent_player != 'torrent2http':
		return

	def check_modify_time(fn):
		import time, filesystem
		mt = filesystem.getmtime(fn)
		if abs(from_time - mt) < 3600:
			return True
		return False

	def get_hashes(fn):
		with filesystem.fopen(fn, 'r') as hf:
			hashes = hf.readlines()
			return [ h.strip('\r\n') for h in hashes ]
		return []

	def rehash_torrent(hashes, torrent_path):
		import time
		try:
			from torrent2httpplayer import Torrent2HTTPPlayer
			from torrent2http import State
		except ImportError:
			return

		player = Torrent2HTTPPlayer(settings)
		player.AddTorrent(torrent_path)
		player.GetLastTorrentData()
		#player.StartBufferFile(0)
		player._AddTorrent(torrent_path)
		player.engine.start()
		f_status = player.engine.file_status(0)

		while True:
			time.sleep(1.0)
			status = player.engine.status()

			if status.state in [State.FINISHED, State.SEEDING, State.DOWNLOADING]:
				break;

		player.engine.wait_on_close()
		player.close()

	def process_dir(_d):
		for fn in filesystem.listdir(_d):
			full_name = filesystem.join(_d, fn)
			if fn.endswith('.hashes') and check_modify_time(full_name):
				hashes = get_hashes(full_name)
				if len(hashes) > 1:
					rehash_torrent(hashes, full_name.replace('.hashes', ''))

	for d in filesystem.listdir(settings.torrents_path()):
		dd = filesystem.join(settings.torrents_path(), d)
		if not filesystem.isfile(dd):
			process_dir(dd)


# ------------------------------------------------------------------------------------------------------------------- #
def update_service(show_progress=False):

	import anidub, hdclub, nnmclub, rutor, soap4me, bluebird, kinohd

	from player import _addon

	anidub_enable		= _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable		= False
	bluebird_enable		= _addon.getSetting('bluebird_enable') == 'true'
	nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'
	rutor_enable		= _addon.getSetting('rutor_enable') == 'true'
	soap4me_enable		= _addon.getSetting('soap4me_enable') == 'true'
	kinohd_enable		= _addon.getSetting('kinohd_enable') == 'true'


	from player import load_settings
	settings = load_settings()

	import time
	from_time = time.time()

	if show_progress:
		import xbmcgui
		info_dialog = xbmcgui.DialogProgressBG()
		info_dialog.create(settings.addon_name)
		settings.progress_dialog = info_dialog
	
	from log import dump_context

	if anidub_enable:
		with dump_context('anidub.run'):
			anidub.run(settings)

	#if hdclub_enable:
	#	hdclub.run(settings)

	if bluebird_enable:
		with dump_context('bluebird.run'):
			bluebird.run(settings)

	if rutor_enable:
		with dump_context('rutor.run'):
			rutor.run(settings)

	if kinohd_enable:
		with dump_context('kinohd.run'):
			kinohd.run(settings)

	if nnmclub_enable:
		from service import Addon
		addon = Addon('settings3.xml')

		try:
			import math
			from time import time
			settings.nnmclub_hours = int(math.ceil((time() - float(addon.getSetting('nnm_last_generate'))) / 3600.0))
		except BaseException as e:
			settings.nnmclub_hours = 168
			log.print_tb(e)

		if settings.nnmclub_hours > 168:
			settings.nnmclub_hours = 168

		if settings.nnmclub_hours < 8:
			settings.nnmclub_hours = 8

		log.debug('NNM hours: ' + str(settings.nnmclub_hours))

		addon.setSetting('nnm_last_generate', str(time()))
		
		with dump_context('nnmclub.run'):
			nnmclub.run(settings)

	#if soap4me_enable:
	#	import soap4me
	#	soap4me.run(settings)

	if show_progress:
		info_dialog.update(0, '', '')
		info_dialog.close()

	if anidub_enable or nnmclub_enable or rutor_enable or soap4me_enable or bluebird_enable or kinohd_enable:
		import xbmc
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video")')

	recheck_torrent_if_need(from_time, settings)


# ------------------------------------------------------------------------------------------------------------------- #
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in xrange(0, len(l), n):
		yield l[i:i + n]


# ------------------------------------------------------------------------------------------------------------------- #
def scrape_nnm():
	from player import load_settings
	settings = load_settings()

	data_path = settings.torrents_path()

	if not filesystem.exists(filesystem.join(data_path, 'nnmclub')):
		return

	hashes = []
	for torr in filesystem.listdir(filesystem.join(data_path, 'nnmclub')):
		if torr.endswith('.torrent'):
			try:
				from base import TorrentPlayer
				tp = TorrentPlayer()
				tp.AddTorrent(filesystem.join(data_path, 'nnmclub', torr))
				data = tp.GetLastTorrentData()
				if data:
					hashes.append((data['announce'], data['info_hash'], torr.replace('.torrent', '.stat')))
			except BaseException as e:
				log.print_tb(e)

	for chunk in chunks(hashes, 32):
		import scraper
		try:
			seeds_peers = scraper.scrape(chunk[0][0], [i[1] for i in chunk], 10)
		except RuntimeError as RunE:
			if '414 status code returned' in RunE.message:
				for c in chunks(chunk, 16):
					try:
						seeds_peers = scraper.scrape(c[0][0], [i[1] for i in c], 10)
						process_chunk(c, data_path, seeds_peers)
					except BaseException as e:
						log.print_tb(e)
			continue
		except BaseException as e:
			log.print_tb(e)
			continue

		process_chunk(chunk, data_path, seeds_peers)


# ------------------------------------------------------------------------------------------------------------------- #
def process_chunk(chunk, data_path, seeds_peers):
	import json

	for item in chunk:
		filename = filesystem.join(data_path, 'nnmclub', item[2])
		remove_file = False
		with filesystem.fopen(filename, 'w') as stat_file:
			try:
				json.dump(seeds_peers[item[1]], stat_file)
			except KeyError:
				remove_file = True
		if remove_file:
			filesystem.remove(filename)

# ------------------------------------------------------------------------------------------------------------------- #
def add_media_process(title, imdb):
	count = 0

	from player import getSetting, load_settings
	import anidub, hdclub, nnmclub, rutor, soap4me, bluebird, kinohd

	settings = load_settings()

	anidub_enable		= getSetting('anidub_enable') == 'true'
	hdclub_enable		= False
	bluebird_enable		= getSetting('bluebird_enable') == 'true'
	nnmclub_enable		= getSetting('nnmclub_enable') == 'true'
	rutor_enable		= getSetting('rutor_enable') == 'true'
	soap4me_enable		= getSetting('soap4me_enable') == 'true'
	kinohd_enable		= getSetting('kinohd_enable') == 'true'

	class RemoteDialogProgress:
		progress_file_path = filesystem.join(addon_data_path(), '.'.join([imdb, 'progress']))

		def update(self, percent, *args, **kwargs):
			with filesystem.fopen(self.progress_file_path, 'w') as progress_file:
				progress_file.write(str(percent) + '\n')
				progress_file.write('\n'.join(args).encode('utf-8'))

		def close(self):
			try:
				filesystem.remove(self.progress_file_path)
			except: pass


	settings.progress_dialog = RemoteDialogProgress()

	p = []

	from log import dump_context
	#try:
	if True:
		if anidub_enable and imdb.startswith('sm'):
			with dump_context('anidub.search_generate'):
				c = anidub.search_generate(title, settings, p)
				count += c

		if imdb.startswith('tt'):
			#if hdclub_enable:
			#	c = hdclub.search_generate(title, imdb, settings, p)
			#	count += c
			if bluebird_enable:
				with dump_context('bluebird.search_generate'):
					c = bluebird.search_generate(title, imdb, settings, p)
					count += c
			if rutor_enable:
				with dump_context('rutor.search_generate'):
					c = rutor.search_generate(title, imdb, settings, p)
					count += c
			if kinohd_enable:
				with dump_context('kinohd.search_generate'):
					c = kinohd.search_generate(title, imdb, settings, p)
					count += c

			if nnmclub_enable:
				with dump_context('nnmclub.search_generate'):
					c = nnmclub.search_generate(title, imdb, settings, p)
					count += c
			#if soap4me_enable:
			#	count += soap4me.search_generate(title, imdb, settings)
	#except BaseException as e:
	#	log.print_tb(e)

	if p:
		path = filesystem.join(addon_data_path(), imdb + '.strm_path')
		with filesystem.fopen(path, 'w') as f:
			f.write(p[0].encode('utf-8'))

	settings.progress_dialog.close()

	if count:
		import xbmc
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			if p and p[0]:
				path = p[0]
				
				if path.endswith('.strm'):
					type = 'movies'
				else:
					type = 'tvshows'

				base_path = filesystem.dirname(p[0])

				from sources import Sources
				srcs = Sources()
				for src in srcs.get('video', normalize=False):
					src_path_basename = filesystem.basename(src.path.rstrip('\\/'))
					if src_path_basename == base_path:  #base_path.lower().replace('\\', '/') in src.path.lower().replace('\\', '/'):
						path_update = src.path
						if type == 'tvshows':
							if src.path.startswith('smb://'):
								path_update = src.path
								path_update = path_update.strip('\\/') + '/' + filesystem.basename(path)
							else:
								path_update = filesystem.join(src.path, filesystem.basename(path))
						log.debug(path_update)
						xbmc.executebuiltin('UpdateLibrary("video","%s")' % path_update.encode('utf-8'))

				#xbmc.executebuiltin('UpdateLibrary("video")')
			else:
				xbmc.executebuiltin('UpdateLibrary("video")')

			xbmc.sleep(250)
			while xbmc.getCondVisibility('Library.IsScanningVideo'):
				xbmc.sleep(100)

	path = filesystem.join(addon_data_path(), imdb + '.ended')
	with filesystem.fopen(path, 'w') as f:
		f.write(str(count))

# ------------------------------------------------------------------------------------------------------------------- #
def clean_movies():
	from kodidb import MoreRequests
	ll = MoreRequests().get_movie_duplicates()

	try:
		from player import load_settings
		settings = load_settings()
	except:
		from settings import Settings
		settings = Settings(filesystem.join(filesystem.dirname(__file__), 'test', 'Videos'))
	
	import movieapi
	from base import make_fullpath
	def clean_movie_by_imdbid(imdbid):
		api = movieapi.MovieAPI(imdbid)
		genre = api['genres']
		if u'мультфильм' in genre:
			base_path = settings.animation_path()
		elif u'документальный' in genre:
			base_path = settings.documentary_path()
		else:
			base_path = settings.movies_path()

		mm = MoreRequests().get_movies_by_imdb(imdbid)

		from base import STRMWriterBase
		from base import Informer

		title = Informer().filename_with(api['title'], api['originaltitle'], api['year'])

		strm_path = filesystem.join(base_path, make_fullpath(title, '.strm'))
		#alt_path = strm_path + '.alternative'
		nfo_path = filesystem.join(base_path, make_fullpath(title, '.nfo'))

		strm_data = filesystem.fopen(mm[0][3], 'r').read()
		alt_data = []
		for m in mm:
			links_with_ranks = STRMWriterBase.get_links_with_ranks(mm[0][3], settings, use_scrape_info=False)
			alt_data.extend(links_with_ranks)

		alt_data = [dict(t) for t in set([tuple(d.iteritems()) for d in alt_data])]
		#alt_data = list(set(alt_data))
		#alt_data.sort(key=operator.itemgetter('rank'))
		with filesystem.save_make_chdir_context(base_path, 'STRMWriterBase.write_alternative'):
			STRMWriterBase.write_alternative(strm_path, alt_data)
		pass


	for m in ll:
		try:
			clean_movie_by_imdbid(m[4])
		except:
			pass

