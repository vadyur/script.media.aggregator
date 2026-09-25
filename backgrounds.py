# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional, Tuple

from vdlib.util import filesystem, log
from vdlib.util.log import dump_context
from movieapi import MovieAPI

def addon_data_path() -> str:
	from player import _addon, _addondir
	if _addon.getSetting('data_path'):
		return _addon.getSetting('data_path')
	else:
		return _addondir

# ------------------------------------------------------------------------------------------------------------------- #
def update_service(show_progress: bool = False) -> None:

	import anidub, nnmclub, rutor

	from player import _addon

	anidub_enable		= _addon.getSetting('anidub_enable') == 'true'
	nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'
	rutor_enable		= _addon.getSetting('rutor_enable') == 'true'


	from player import load_settings
	settings = load_settings()

	if show_progress:
		import xbmcgui
		info_dialog = xbmcgui.DialogProgressBG()
		info_dialog.create(settings.addon_name)
		settings.progress_dialog = info_dialog

	if anidub_enable:
		with dump_context('anidub.run'):
			anidub.run(settings)

	if rutor_enable:
		with dump_context('rutor.run'):
			rutor.run(settings)

	if nnmclub_enable:
		from service import Addon
		addon = Addon('settings3.xml')

		try:
			import math
			from time import time
			settings.nnmclub_hours = int(math.ceil((time() - float(addon.getSetting('nnm_last_generate'))) / 3600.0))
		except BaseException as e:
			settings.nnmclub_hours = 168
			#log.print_tb(e)

		if settings.nnmclub_hours > 168:
			settings.nnmclub_hours = 168

		if settings.nnmclub_hours < 8:
			settings.nnmclub_hours = 8

		log.debug('NNM hours: ' + str(settings.nnmclub_hours))

		try:
			addon.setSetting('nnm_last_generate', str(time()))
		except BaseException as e:
			pass
		
		with dump_context('nnmclub.run'):
			nnmclub.run(settings)

	if show_progress:
		info_dialog.update(0)
		info_dialog.close()

	if settings.update_paths:
		from plugin import UpdateVideoLibrary, ScanMonitor

		monitor = ScanMonitor()
		UpdateVideoLibrary()
		while not monitor.abortRequested():
			if monitor.waitForAbort(1):
				return
			if monitor.do_exit:
				clean_movies()
				clean_tvshows()
				break


# ------------------------------------------------------------------------------------------------------------------- #
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]


# ------------------------------------------------------------------------------------------------------------------- #
def scrape_nnm() -> None:
	from player import load_settings
	settings = load_settings()

	data_path = settings.torrents_path()

	if not filesystem.exists(filesystem.join(data_path, 'nnmclub')):
		return

	hashes = []
	for torr in filesystem.listdir(filesystem.join(data_path, 'nnmclub')):
		if torr.endswith('.torrent'):
			try:
				from vdlib.torrent.torrentplayer import TorrentPlayer
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
			if '414 status code returned' in str(RunE):
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
def add_media_process(title: str, imdb: str) -> None:
	count = 0

	from player import getSetting, load_settings
	import anidub, nnmclub, rutor

	settings = load_settings()

	anidub_enable		= getSetting('anidub_enable') == 'true'
	nnmclub_enable		= getSetting('nnmclub_enable') == 'true'
	rutor_enable		= getSetting('rutor_enable') == 'true'

	class RemoteDialogProgress:
		progress_file_path = filesystem.join(addon_data_path(), '.'.join([imdb, 'progress']))

		def update(self, percent, *args, **kwargs):
			with filesystem.fopen(self.progress_file_path, 'w') as progress_file:
				progress_file.write(str(percent) + '\n')
				progress_file.write('\n'.join(str(a) for a in args))

		def close(self):
			try:
				filesystem.remove(self.progress_file_path)
			except: pass


	settings.progress_dialog = RemoteDialogProgress()

	p = []  # type: List[str]

	if anidub_enable and imdb.startswith('sm'):
		with dump_context('anidub.search_generate'):
			c = anidub.search_generate(title, settings, p)
			count += c

	if imdb.startswith('tt'):
		if rutor_enable:
			with dump_context('rutor.search_generate'):
				c = rutor.search_generate(title, imdb, settings, p)
				count += c

		if nnmclub_enable:
			with dump_context('nnmclub.search_generate'):
				c = nnmclub.search_generate(title, imdb, settings, p)
				count += c

	if p:
		path = filesystem.join(addon_data_path(), imdb + '.strm_path')
		with filesystem.fopen(path, 'w') as f:
			f.write(p[0])

	settings.progress_dialog.close()

	if count:
		import xbmc
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			from plugin import UpdateVideoLibrary
			if p and p[0]:
				path = p[0]
				
				if path.endswith('.strm'):
					type = 'movies'
				else:
					type = 'tvshows'

				base_path = filesystem.dirname(p[0])

				from vdlib.kodi.sources import Sources
				srcs = Sources()
				for src in srcs.get('video', normalize=False):
					src_path_basename = filesystem.basename(src.path.rstrip('\\/'))
					if base_path.startswith(src_path_basename):
						if type == 'tvshows':
							path_update = src.path
							if src.path.startswith('smb://'):
								path_update = src.path
								path_update = path_update.strip('\\/') + '/' + filesystem.basename(path)
							else:
								path_update = filesystem.join(src.path, filesystem.basename(path))
						else:
							path_update = filesystem.join( src.path, base_path[len(src_path_basename)+1:] )
						log.debug(path_update)
						#VideoLibrary.Scan(directory=path_update)
						UpdateVideoLibrary(path=path_update)
			else:
				UpdateVideoLibrary()

	clean_movies()
	clean_tvshows()

	path = filesystem.join(addon_data_path(), imdb + '.ended')
	with filesystem.fopen(path, 'w') as f:
		f.write(str(count))


def load_settings():
	from player import load_settings as _load_settings
	return _load_settings()

def safe_remove(path: str) -> None:
	if filesystem.exists(path):
		filesystem.remove(path)

def safe_copyfile(src: str, dst: str) -> None:
	dirname = filesystem.dirname(dst)
	if not filesystem.exists(dirname):
		filesystem.makedirs(dirname)

	if filesystem.exists(src):
		filesystem.copyfile(src, dst)

def dt(ss):
	import datetime
	# 2017-11-30 02:29:57
	fmt = '%Y-%m-%d %H:%M:%S'
	try:
		return datetime.datetime.strptime(ss, fmt)
	except:
		return 0


# ------------------------------------------------------------------------------------------------------------------- #
def clean_movies() -> None:
	_debug = False

	from plugin import wait_for_update
	wait_for_update()

	log.debug('*'*80)
	log.debug('* Start cleaning movies')
	log.debug('*'*80)

	from vdlib.kodi.kodidb import MoreRequests
	more_requests = MoreRequests()

	movie_duplicates_list = more_requests.get_movie_duplicates()

	if not movie_duplicates_list:
		return

	settings = load_settings()

	watched_and_progress = {}
	update_paths = set()
	clean_ids = []
	
	import movieapi
	from vdlib.util.base import make_fullpath
	def get_info_and_move_files(imdbid: str) -> Dict[str, Any]:
		def _log(s):
			log.debug('    get_info_and_move_files: {}'.format(s))

		api = movieapi.MovieAPI.get_by(imdb_id=imdbid)[0]

		try:
			genre = api['genres']
			if 'мультфильм' in genre:
				base_path = settings.animation_path()
			elif 'документальный' in genre:
				base_path = settings.documentary_path()
			else:
				base_path = settings.movies_path()
		except:
			base_path = settings.movies_path()

		from movieapi import make_imdb_path
		base_path = make_imdb_path(base_path, imdbid)

		one_movie_duplicates = [x for x in more_requests.get_movies_by_imdb(imdbid) if x['c22'].endswith('.strm')]

		from base import STRMWriterBase
		from base import Informer

		# то же правило имени, что и при генерации (Informer.make_filename_imdb), иначе файлы будут переименовываться туда-обратно
		title = Informer().filename_with(api.get('title'), api.get('originaltitle'), api.get('year'))
			
		strm_path = filesystem.join(base_path, make_fullpath(title, '.strm'))
		nfo_path = filesystem.join(base_path, make_fullpath(title, '.nfo'))

		_log('title = ' + title)
		_log('strm_path = ' + strm_path)

		#strm_data = filesystem.fopen(one_movie_duplicates[0]['c22'], 'r').read()
		alt_data = []

		update_fields = {}

		movie_duplicate = None
		for movie_duplicate in one_movie_duplicates:
			links_with_ranks = STRMWriterBase.get_links_with_ranks(movie_duplicate['c22'], settings, use_scrape_info=False)
			alt_data.extend(links_with_ranks)

			# Sync playCount & resume time
			if movie_duplicate['playCount']:
				update_fields['playcount'] = int(update_fields.get('playcount', 0)) + int(movie_duplicate['playCount'])

			if movie_duplicate['resumeTimeInSeconds'] and movie_duplicate['totalTimeInSeconds']:
				update_fields['resume']			= {
					'position': int(movie_duplicate['resumeTimeInSeconds']),
					'total':	int(movie_duplicate['totalTimeInSeconds'])}

		with filesystem.save_make_chdir_context(base_path, 'STRMWriterBase.write_alternative'):
			alt_data = [dict(t) for t in set([tuple(d.items()) for d in alt_data])]
			STRMWriterBase.write_alternative(strm_path, alt_data)

			if movie_duplicate:
				last_strm_path = movie_duplicate['c22']
				if last_strm_path != strm_path:
					last_nfo_path = last_strm_path.replace('.strm', '.nfo')

					safe_copyfile(last_strm_path, strm_path)
					safe_copyfile(last_nfo_path, nfo_path)

					update_paths.add(filesystem.dirname(strm_path))

			for movie_duplicate in one_movie_duplicates:
				cur_strm_path = movie_duplicate['c22']
				if cur_strm_path != strm_path:
					safe_remove(cur_strm_path)
					safe_remove(cur_strm_path.replace('.strm', '.nfo'))
					safe_remove(cur_strm_path + '.alternative')

					clean_ids.append(movie_duplicate['idMovie'])

		return update_fields


	log.debug('# ----------------')
	log.debug('# Get info & move files')
	for movie in movie_duplicates_list:
		try:
			imdbid = movie[0]
			watched_and_progress[imdbid] = get_info_and_move_files(imdbid)
		except BaseException as e:
			log.print_tb(e)

		if _debug:
			break

	log.debug('# ----------------')
	log.debug('# Update Video library')
	from vdlib.kodi.jsonrpc_requests import VideoLibrary
	from plugin import wait_for_update, UpdateVideoLibrary

	#ver = JSONRPC.Version()
	for path in update_paths:
		log.debug('Scan for: {}'.format(path))
		#VideoLibrary.Scan(directory=path)
		#wait_for_update()
		UpdateVideoLibrary(path=path, wait=True)

	#res = VideoLibrary.Clean(showdialogs=_debug)
	#log.debug(unicode(res))

	log.debug('# ----------------')
	log.debug('# Apply watched & progress')
	for imdbid, update_data in watched_and_progress.items():
		if update_data:
			movies = more_requests.get_movies_by_imdb(imdbid)
			if movies:
				movieid = movies[-1]['idMovie']
				log.debug('Process {}'.format(movies[-1]['c22']))
				log.debug(str(update_data))
				VideoLibrary.SetMovieDetails(movieid=movieid, **update_data)
		pass

	log.debug('# ----------------')
	log.debug('# Clean movies')
	for idMovie in clean_ids:
		log.debug('remove movie: {}'.format(idMovie))
		VideoLibrary.RemoveMovie(movieid=idMovie)

	log.debug('*'*80)
	log.debug('* End cleaning movies')
	log.debug('*'*80)


# ------------------------------------------------------------------------------------------------------------------- #
# Чистка дублей сериалов
#
# Папка сериала называется '<оригинальное название> (<год>)' (см. tvshowapi.tvshow_dirname). Папки со старыми именами
# или дубли одного сериала сливаются в папку с правильным именем, старый сериал удаляется из медиатеки,
# а отметки о просмотре и позиции эпизодов переносятся на новый.
# ------------------------------------------------------------------------------------------------------------------- #
EpisodeKey = Tuple[int, int]


def _norm_path(path: str) -> str:
	import os
	path = filesystem.normseps(path).rstrip('\\/')
	return path.lower() if os.name == 'nt' else path


def _rmtree(path: str) -> None:
	import os
	if filesystem.use_xbmcvfs:
		import xbmcvfs
		xbmcvfs.rmdir(filesystem.xbmcvfs_path(path.rstrip('\\/') + os.sep), True)
	else:
		import shutil
		shutil.rmtree(filesystem.real_path(path), ignore_errors=True)


def _fix_strm_path(strm_file: str, settings) -> None:
	"""Параметр path в ссылке .strm - папка сезона относительно медиатеки; после переноса он другой."""
	import urllib.parse
	with filesystem.fopen(strm_file, 'r') as f:
		link = f.read()

	head, sep, tail = link.partition('&path=')
	if not sep:
		return

	new_rel = filesystem.relpath(filesystem.dirname(strm_file), settings.base_path())
	rest = tail.split('&', 1)
	new_link = head + '&path=' + urllib.parse.quote(new_rel) + ('&' + rest[1] if len(rest) > 1 else '')
	if new_link != link:
		with filesystem.fopen(strm_file, 'w') as f:
			f.write(new_link)


def _merge_tvshow_dir(src: str, dst: str, settings) -> None:
	"""Переносит файлы сериала из src в dst: недостающие копируются, списки раздач .alternative объединяются."""
	from base import STRMWriterBase

	if not filesystem.exists(dst):
		filesystem.makedirs(dst)

	for name in filesystem.listdir(src):
		src_item = filesystem.join(src, name)
		dst_item = filesystem.join(dst, name)

		if not filesystem.isfile(src_item):
			_merge_tvshow_dir(src_item, dst_item, settings)
			continue

		if not filesystem.exists(dst_item):
			filesystem.copyfile(src_item, dst_item)
			if name.endswith('.strm'):
				_fix_strm_path(dst_item, settings)
		elif name.endswith('.strm.alternative'):
			strm_src = src_item[:-len('.alternative')]
			strm_dst = dst_item[:-len('.alternative')]
			links = STRMWriterBase.get_links_with_ranks(strm_dst, settings) + \
					STRMWriterBase.get_links_with_ranks(strm_src, settings)
			unique = {}  # type: Dict[str, Dict[str, Any]]
			for item in links:
				unique.setdefault(item['link'], item)
			STRMWriterBase.write_alternative(strm_dst, list(unique.values()))


def _library_tvshows() -> List[Dict[str, Any]]:
	from vdlib.kodi.jsonrpc_requests import VideoLibrary
	return VideoLibrary.GetTVShows(properties=['file', 'imdbnumber']).get('tvshows', [])


def _find_tvshow_id(path: str, shows: List[Dict[str, Any]]) -> Optional[int]:
	for show in shows:
		if _norm_path(show.get('file', '')) == _norm_path(path):
			return show['tvshowid']
	return None


def _episodes_state(tvshowid: int) -> Dict[EpisodeKey, Dict[str, Any]]:
	from vdlib.kodi.jsonrpc_requests import VideoLibrary
	result = VideoLibrary.GetEpisodes(tvshowid=tvshowid, properties=['season', 'episode', 'playcount', 'resume'])
	state = {}  # type: Dict[EpisodeKey, Dict[str, Any]]
	for e in result.get('episodes', []):
		state[(e['season'], e['episode'])] = {'episodeid': e['episodeid'],
											  'playcount': e.get('playcount', 0),
											  'resume': e.get('resume', {})}
	return state


def _restore_episodes_state(tvshowid: int, saved: List[Dict[EpisodeKey, Dict[str, Any]]]) -> None:
	from vdlib.kodi.jsonrpc_requests import VideoLibrary

	for key, current in _episodes_state(tvshowid).items():
		params = {}  # type: Dict[str, Any]
		playcount = max([s[key].get('playcount', 0) for s in saved if key in s] + [0])
		if playcount > current['playcount']:
			params['playcount'] = playcount

		if not current['resume'].get('position'):
			for s in saved:
				resume = s.get(key, {}).get('resume', {})
				if resume.get('position') and resume.get('total'):
					params['resume'] = {'position': resume['position'], 'total': resume['total']}
					break

		if params:
			log.debug('    restore S{}E{}: {}'.format(key[0], key[1], params))
			VideoLibrary.SetEpisodeDetails(episodeid=current['episodeid'], **params)


def _tvshow_groups(root: str) -> Dict[Tuple[str, str], List[Tuple[str, Dict[str, Any]]]]:
	"""Папки сериалов категории, сгруппированные по IMDb id (или по оригинальному названию, если id нет)."""
	from nforeader import NFOReader
	from base import original_name

	groups = {}  # type: Dict[Tuple[str, str], List[Tuple[str, Dict[str, Any]]]]
	for d in filesystem.listdir(root):
		nfo = filesystem.join(root, d, 'tvshow.nfo')
		if not filesystem.exists(nfo):
			continue
		try:
			reader = NFOReader(nfo, '')
			imdb = reader.imdb_id()
			info = reader.get_info()
		except Exception as e:
			log.print_tb(e)
			continue

		if imdb:
			key = ('imdb', imdb)
		else:
			name = original_name(info.get('title'), info.get('originaltitle'))
			if not name:
				continue
			key = ('title', name.lower())
		groups.setdefault(key, []).append((d, info))
	return groups


def _canonical_tvshow_dir(key: Tuple[str, str], info: Dict[str, Any]) -> Optional[str]:
	import movieapi, tvshowapi
	from base import original_name
	from vdlib.util.base import make_fullpath

	if key[0] == 'imdb':
		name = tvshowapi.tvshow_name_from_api(movieapi.MovieAPI.get_by(imdb_id=key[1])[0])
	else:
		name = original_name(info.get('title'), info.get('originaltitle'))

	return make_fullpath(name, '') if name else None


def clean_tvshows() -> None:
	from plugin import wait_for_update, UpdateVideoLibrary
	from vdlib.kodi.jsonrpc_requests import VideoLibrary

	wait_for_update()

	log.debug('*'*80)
	log.debug('* Start cleaning tvshows')
	log.debug('*'*80)

	settings = load_settings()
	roots = [path for enabled, path in [
				(settings.tvshows_save, settings.tvshow_path()),
				(settings.animation_tvshows_save, settings.animation_tvshow_path()),
				(settings.anime_save, settings.anime_tvshow_path())] if enabled and filesystem.exists(path)]

	shows = None  # type: Optional[List[Dict[str, Any]]]
	saved_states = {}  # type: Dict[str, List[Dict[EpisodeKey, Dict[str, Any]]]]

	for root in roots:
		for key, dirs in _tvshow_groups(root).items():
			try:
				canonical = _canonical_tvshow_dir(key, dirs[0][1])
				if not canonical:
					continue

				old_dirs = [d for d, _ in dirs if d != canonical]
				if not old_dirs:
					continue

				dst = filesystem.join(root, canonical)
				if shows is None:
					shows = _library_tvshows()

				for d in old_dirs:
					src = filesystem.join(root, d)
					log.debug('merge tvshow: "{}" -> "{}"'.format(d, canonical))

					tvshowid = _find_tvshow_id(src, shows)
					if tvshowid is not None:
						saved_states.setdefault(dst, []).append(_episodes_state(tvshowid))

					_merge_tvshow_dir(src, dst, settings)
					_rmtree(src)

					if tvshowid is not None:
						VideoLibrary.RemoveTVShow(tvshowid=tvshowid)

				saved_states.setdefault(dst, [])
			except BaseException as e:
				log.print_tb(e)

	for dst in saved_states:
		log.debug('Scan for: {}'.format(dst))
		UpdateVideoLibrary(path=dst, wait=True)

	if any(saved_states.values()):
		shows = _library_tvshows()
		for dst, states in saved_states.items():
			tvshowid = _find_tvshow_id(dst, shows)
			if tvshowid is not None and states:
				_restore_episodes_state(tvshowid, states)

	log.debug('*'*80)
	log.debug('* End cleaning tvshows')
	log.debug('*'*80)
