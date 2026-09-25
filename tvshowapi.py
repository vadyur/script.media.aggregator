# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from vdlib.util.log import debug, print_tb
from vdlib.util import filesystem
from vdlib.util.base import make_fullpath

# Разбор имён файлов и API сериалов живут в vdlib
from vdlib.scrappers.tvshowapi import cutStr, sweetpair, sortext, cutFileNames, FileNamesPrepare, get_list, \
	seasonfromname, season_from_title, TheTVDBAPI, MyShowsAPI, TVShowAPI
from vdlib.scrappers.tvshowapi import parse_torrent as _parse_torrent_info


def _to_str(value: Any, skip_keys: tuple = (b'pieces',)) -> Any:
	"""Рекурсивно приводит bencode-данные (bytes) к str, пропуская бинарные поля."""
	if isinstance(value, bytes):
		return value.decode('utf-8', 'replace')
	if isinstance(value, list):
		return [_to_str(v, skip_keys) for v in value]
	if isinstance(value, dict):
		result = {}  # type: Dict[str, Any]
		for k, v in value.items():
			if k in skip_keys:
				continue
			result[_to_str(k)] = _to_str(v, skip_keys)
		return result
	return value


def torrent_info(data: bytes) -> Optional[Dict[str, Any]]:
	"""Раздел info торрента со str-ключами; поля *.utf-8 подменяют обычные."""
	from vdlib.torrent.bencodepy import bdecode, BencodeDecodeError
	try:
		decoded = bdecode(data)
	except BencodeDecodeError:
		debug("Can't decode torrent data (invalid torrent link?)")
		return None

	info = _to_str(decoded[b'info'])
	if 'name.utf-8' in info:
		info['name'] = info['name.utf-8']
	for f in info.get('files', []):
		if 'path.utf-8' in f:
			f['path'] = f['path.utf-8']
	return info


def parse_torrent(data: bytes, season: Optional[int] = None) -> List[Dict[str, Any]]:
	info = torrent_info(data)
	if info is None:
		return []
	return _parse_torrent_info(info, season)


def write_tvshow(fulltitle: str, link: str, settings, parser, path: str, skip_nfo_exists: bool = False) -> Optional[str]:
	from nfowriter import NFOWriter
	from strmwriter import STRMWriter

	from downloader import TorrentDownloader
	dl = TorrentDownloader(parser.link(), settings.torrents_path(), settings)
	if not dl.download():
		return None

	with filesystem.fopen(dl.get_filename(), 'rb') as torr:
		content = torr.read()
	files = parse_torrent(content, season_from_title(fulltitle))

	title = parser.get_value('title')
	debug(title)
	originaltitle = parser.get_value('originaltitle')
	debug(originaltitle)

	imdb_id = parser.get('imdb_id', None)
	tvshow_api = TVShowAPI.get_by(originaltitle, title, imdb_id)

	api_title = None  # type: Optional[str]
	try:
		api_title = parser.movie_api().imdbapi.title()
	except Exception:
		pass
	if not api_title:
		try:
			api_title = parser.movie_api()['title']
		except Exception:
			pass
	if not api_title:
		api_title = tvshow_api.Title()
	tvshow_path = make_fullpath(api_title if api_title is not None else title, '')
	debug(tvshow_path)

	if not tvshow_path:
		return None

	tvshow_path = filesystem.join(path, tvshow_path)
	with filesystem.save_make_chdir_context(tvshow_path, 'tvshowapi.write_tvshow'):

		NFOWriter(parser, tvshow_api=tvshow_api, movie_api=parser.movie_api()).write_tvshow_nfo(tvshow_path)

		for f in files:
			s_num = f['season'] if f['season'] else 1
			try:
				episode = tvshow_api.Episode(s_num, f['episode'])
				if not episode:
					episode = {
						'title': title,
						'seasonNumber': s_num,
						'episodeNumber': f['episode'],
						'image': '',
						'airDate': ''
					}

				season_path = 'Season %d' % s_num
			except BaseException as e:
				print_tb(e)
				continue

			season_path = filesystem.join(tvshow_path, season_path)
			with filesystem.save_make_chdir_context(season_path, 'tvshowapi.write_tvshow2'):

				results = [x for x in files if x['season'] == s_num and x['episode'] == f['episode']]
				if len(results) > 1:	# Has duplicate episodes
					filename = f['name']
				else:
					try:
						cnt = f['episode']
						filename = '%02d. episode_s%02de%02d' % (cnt, s_num, f['episode'])
					except BaseException as e:
						print_tb(e)
						filename = f['name']

				debug(filename)

				STRMWriter(parser.link()).write(filename, season_path, index=f['index'], settings=settings, parser=parser)
				NFOWriter(parser, tvshow_api=tvshow_api, movie_api=parser.movie_api()).write_episode(episode, filename, season_path, skip_nfo_exists=skip_nfo_exists)

	settings.update_paths.add(tvshow_path)
	return tvshow_path
