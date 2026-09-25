# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from vdlib.util import log
from vdlib.util.log import debug
from vdlib.util import filesystem

import os, re
from settings import *
import urllib.parse
from movieapi import *
import operator

# Общие утилиты перенесены в vdlib; реэкспортируются для модулей, делающих `from base import *`
from vdlib.util.base import KB, MB, GB, make_fullpath, remove_script_tags, clean_html, striphtml, \
	detect_mpg, detect_h264, detect_h265
from vdlib.torrent.torrentplayer import TorrentPlayer
from vdlib.torrent.bencodepy import bdecode, bencode, BencodeDecodeError


def lower(s: str) -> str:
	s = s.lower()
	_s = str()
	for ch in s:
		if ord(ch) >= ord('А') and ord(ch) <= ord('Я'):
			ofs = ord('а') - ord('А')
			_s += chr(ord(ch) + ofs)
		else:
			_s += ch
	return _s


def skipped(item) -> None:
	debug(item.title + '\t\t\t[Skipped]')


def is_torrent_remembed(parser: Dict[str, Any], settings) -> bool:
	from downloader import TorrentDownloader
	link = parser.get('link').split('torrent=')[-1]
	if link:
		torr_downloader = TorrentDownloader(urllib.parse.unquote(link), None, settings)
		path = filesystem.join(settings.torrents_path(), torr_downloader.get_subdir_name(), torr_downloader.get_post_index() + '.choice')
		return filesystem.exists(path)

	return False


def get_rank(full_title: str, parser: Dict[str, Any], settings) -> float:

	preffered_resolution_v = 1080
	try:
		if settings.preffered_type == QulityType.Q720:
			preffered_resolution_v = 720
		elif settings.preffered_type == QulityType.Q2160:
			preffered_resolution_v = 2160
	except BaseException as e:
		log.print_tb(e)

	preffered_bitrate	= settings.preffered_bitrate

	rank = 0.0
	conditions = 0
	mults = []  # type: List[float]

	if '[ad]' in full_title.lower():
		mults.append(1.1)

	if 'seeds' in parser:
		seeds = int(parser['seeds'])
		if seeds == 0:
			mults.append(10)
		else:
			v = 1.0 + 0.25 / seeds
			mults.append(v)
	else:
		mults.append(1.25)

	res_v = 1080
	if '720p' in full_title:
		res_v = 720

	if '2160' in full_title:
		res_v = 2160

	video = parser.get('video', '')
	if video:
		parts = video.split(', ')
	else:
		parts = []

	for part in parts:
		multiplier = 0
		if 'kbps' in part \
			or 'kbs' in part \
			or 'Kbps' in part \
			or 'Кбит/сек' in part \
			or 'Кбит/с' in part \
			or 'Kb/s' in part:
				multiplier = 1
		if 'mbps' in part \
			or 'mbs' in part \
			or 'Mbps' in part \
			or 'Мбит/сек' in part \
			or 'Mбит/с' in part \
			or 'Мбит/с' in part \
			or 'Mb/s' in part \
			or 'mb/s' in part:
				multiplier = 1000
		if multiplier != 0:
			find = re.findall(r'[\d\.,]', part.split('(')[0])
			bitrate = ''.join(find).replace(',', '.')
			try:
				if bitrate != '' and float(bitrate) != 0 and float(bitrate) < 50000:
					debug('bitrate: %d kbps' % int(float(bitrate) * multiplier))
					if float(bitrate) * multiplier > preffered_bitrate:
						rank += (float(bitrate) * multiplier) / preffered_bitrate
					else:
						rank += preffered_bitrate / (float(bitrate) * multiplier)
					conditions += 1
				else:
					mults.append(1.5)
					debug('bitrate: not parsed')
			except:
				mults.append(1.5)
				debug('bitrate: not parsed')

		if '3840x' in part or 'x2160' in part:
			res_v = 2160
		if '1920x' in part or 'x1080' in part:
			res_v = 1080
		if '1280x' in part or 'x720' in part:
			res_v = 720
		if '720x' in part or 'x540' in part:
			res_v = 540

	if abs(preffered_resolution_v - res_v) > 360:
		rank += 5
		conditions += 1
	elif abs(preffered_resolution_v - res_v) > 0:
		rank += 2
		conditions += 1

	detect_codec = None

	if detect_h264(full_title):
		detect_codec = CodecType.MPGHD
	elif detect_h265(full_title):
		detect_codec = CodecType.MPGUHD
	elif detect_mpg(full_title):
		detect_codec = CodecType.MPGSD

	if detect_codec is None:
		for part in parts:
			if detect_h264(part):
				detect_codec = CodecType.MPGHD
			elif detect_h265(part):
				detect_codec = CodecType.MPGUHD
			elif detect_mpg(part):
				detect_codec = CodecType.MPGSD

	if detect_codec:
		if settings.preffered_codec == CodecType.MPGSD:
			if settings.preffered_codec != detect_codec:
				rank += 10
				conditions += 1
		elif settings.preffered_codec == CodecType.MPGHD:
			if detect_codec == CodecType.MPGUHD:
				rank += 10
				conditions += 1
			if detect_codec == CodecType.MPGSD:
				rank += 2
				conditions += 1
		elif settings.preffered_codec == CodecType.MPGUHD:
			if settings.preffered_codec != detect_codec:
				rank += 2
				conditions += 1

	if 'ISO' in parser.get('format', ''):
		rank += 100
		conditions += 1

	if conditions != 0:
		rank /= conditions
	else:
		rank = 1.0

	for m in mults:
		rank *= m

	if is_torrent_remembed(parser, settings):
		rank /= 1000

	return rank


def make_utf8(s: Any) -> str:
	# Историческое имя: раньше кодировало в utf-8 байты, теперь просто приводит к str
	return s if isinstance(s, str) else str(s)


def _bstr(value: Any) -> str:
	return value.decode('utf-8', 'replace') if isinstance(value, bytes) else str(value)


def scrape_now(fn: str) -> Dict[str, Any]:
	debug(fn)
	with filesystem.fopen(fn, 'rb') as fin:
		try:
			decoded = bdecode(fin.read())
		except BencodeDecodeError:
			debug("Can't decode torrent data (invalid torrent link?)")
			return {}

	import hashlib
	info_hash = hashlib.sha1(bencode(decoded[b'info'])).hexdigest()

	hashes = [info_hash]
	import scraper

	result = []  # type: List[Dict[str, Any]]
	threads = []

	def start_scrape(announce: str) -> None:
		def do_scrape():
			try:
				res = scraper.scrape(announce, hashes, 0.25)
				result.append(res[info_hash])
			except:
				debug(announce + ' - not working')

		import threading
		t = threading.Thread(target=do_scrape)
		threads.append(t)
		t.start()

	if b'announce-list' in decoded:
		for announce in decoded[b'announce-list']:
			start_scrape(_bstr(announce[0]))

		alive = True
		while not result and alive:
			alive = False
			for t in threads:
				if t.is_alive():
					alive = True
					break
	elif b'announce' in decoded:
		res = scraper.scrape(_bstr(decoded[b'announce']), hashes)
		return res[info_hash]

	if result:
		return result[0]

	return {}


def seeds_peers(item: Dict[str, Any]) -> Dict[str, Any]:
	res = {}  # type: Dict[str, Any]
	try:
		link = urllib.parse.unquote(item['link'])
		try:
			import player
			settings = player.load_settings()
		except:
			settings = Settings.current_settings
		if 'nnm-club' in link or 'nnmclub' in link:
			debug('seeds_peers: ' + link)
			t_id = re.search(r't=(\d+)', link).group(1)
			fn = filesystem.join(settings.torrents_path(), 'nnmclub', t_id + '.stat')
			debug(fn)
			with filesystem.fopen(fn, 'r') as stat_file:
				import json
				res = json.load(stat_file)
				debug(str(res))
		elif 'rutor' in link:
			t_id = re.search(r'/torrent/(\d+)', link).group(1)
			fn = filesystem.join(settings.torrents_path(), 'rutor', t_id + '.torrent')
			return scrape_now(fn)

	except BaseException as e:
		debug(str(e))
	return res


class STRMWriterBase(object):
	def make_alternative(self, strmFilename: str, link: str, parser) -> None:
		strmFilename_alt = strmFilename + '.alternative'

		s_alt = ''
		if filesystem.isfile(strmFilename_alt):
			with filesystem.fopen(strmFilename_alt, "r") as alternative:
				s_alt = alternative.read()

		if not (link in s_alt):
			try:
				with filesystem.fopen(strmFilename_alt, "a+") as alternative:
					for key, value in parser.Dict().items():
						if key in ['director', 'studio', 'country', 'plot', 'actor', 'genre', 'country_studio']:
							continue
						alternative.write('#%s=%s\n' % (make_utf8(key), make_utf8(value)))
					alternative.write(link + '\n')
			except:
				log.print_tb()


	@staticmethod
	def get_links_with_ranks(strmFilename: str, settings, use_scrape_info: bool = False) -> List[Dict[str, Any]]:
		strmFilename_alt = get_true_filename(strmFilename + '.alternative')

		items = []  # type: List[Dict[str, Any]]
		saved_dict = {}  # type: Dict[str, Any]
		if filesystem.isfile(strmFilename_alt):
			with filesystem.fopen(strmFilename_alt, "r") as alternative:
				curr_rank = 1.0
				while True:
					line = alternative.readline()
					if not line:
						break
					if line.startswith('#'):
						line = line.lstrip('#')
						parts = line.split('=')
						if len(parts) > 1:
							saved_dict[parts[0]] = parts[1].strip(' \n\t\r')
					elif line.startswith('plugin://script.media.aggregator'):
						try:
							saved_dict['link'] = line.strip('\r\n\t ')
							if use_scrape_info:
								sp = seeds_peers(saved_dict)
								saved_dict = dict(saved_dict, **sp)
							if 'rank' in saved_dict:
								curr_rank = float(saved_dict['rank'])
							else:
								curr_rank = get_rank(saved_dict.get('full_title', ''), saved_dict, settings)
						except BaseException as e:
							log.print_tb(e)
							curr_rank = 1.0

						item = {'rank': curr_rank, 'link': line.strip('\r\n\t ')}
						items.append(dict(item, **saved_dict))
						saved_dict.clear()

		items.sort(key=operator.itemgetter('rank'))
		return items


	@staticmethod
	def get_link_with_min_rank(strmFilename: str, settings) -> Optional[str]:
		items = STRMWriterBase.get_links_with_ranks(strmFilename, settings)

		if len(items) == 0:
			return None
		else:
			return items[0]['link']

	@staticmethod
	def has_link(strmFilename: str, link: str) -> bool:
		strmFilename_alt = strmFilename + '.alternative'
		if filesystem.isfile(strmFilename_alt):
			with filesystem.fopen(strmFilename_alt, "r") as alternative:
				for line in alternative:
					if line.startswith('plugin://'):
						if link in urllib.parse.unquote(line):
							return True
		return False

	@staticmethod
	def write_alternative(strmFilename: str, links_with_ranks: List[Dict[str, Any]]) -> None:
		strmFilename_alt = strmFilename + '.alternative'
		with filesystem.fopen(strmFilename_alt, 'w') as alternative:
			for variant in links_with_ranks:
				if 'link' in variant:
					for k, v in variant.items():
						if k != 'link':
							alternative.write('#%s=%s\n' % (make_utf8(k), make_utf8(v)))

					alternative.write( make_utf8(variant['link']) + '\n')


class EmptyMovieApi(object):
	def get(self, key, default=None):
		return default
	def __getitem__(self, key):
		raise AttributeError


class Informer(object):
	def __init__(self):
		self.__movie_api = EmptyMovieApi()

	def make_movie_api(self, imdb_id: Optional[str], kp_id: Optional[str] = None, settings = None) -> None:
		# kp_id оставлен для совместимости с трекерами; API Кинопоиска больше нет
		orig=None
		year=None

		if not imdb_id:
			if 'originaltitle' in self.Dict():
				orig = self.Dict()['originaltitle']
			if 'year' in self.Dict():
				year = self.Dict()['year']

		from movieapi import MovieAPI
		self.__movie_api, imdb_id = MovieAPI.get_by(imdb_id=imdb_id, orig=orig, year=year, settings=settings)
		if imdb_id:
			self.Dict()['imdb_id'] = imdb_id

	def movie_api(self):
		return self.__movie_api

	def filename_with(self, title: str, originaltitle: str, year: Any) -> str:
		if title == originaltitle:
			filename = title
		elif title == '' and originaltitle != '':
			filename = originaltitle
		elif title != '' and originaltitle == '':
			filename = title
		else:
			filename = originaltitle

		# Год дописывается всегда (как и раньше), чтобы не менялись имена уже созданных файлов
		filename += ' (' + str(year) + ')'

		return filename

	def make_filename_imdb(self) -> Optional[str]:
		if self.__movie_api:
			title 			= self.__movie_api.imdbapi.title()
			originaltitle	= self.__movie_api.imdbapi.originaltitle()
			try:
				year		= self.__movie_api['year']
			except AttributeError:
				year = None

			return self.filename_with(title, originaltitle, year)

		return None

class DescriptionParserBase(Informer):
	_dict = {}  # type: Dict[str, Any]

	def Dump(self) -> None:
		debug('-------------------------------------------------------------------------')
		for key, value in self._dict.items():
			debug('{}\t: {}'.format(key, value))

	def Dict(self) -> Dict[str, Any]:
		return self._dict

	def get_value(self, tag: str, def_value: Any = '') -> Any:
		try:
			return self._dict[tag]
		except:
			return def_value

	def get(self, tag: str, def_value: Any) -> Any:
		return self._dict.get(tag, def_value)

	def parsed(self) -> bool:
		return self.OK

	def parse(self) -> bool:
		raise NotImplementedError("def parse(self): not imlemented.\nPlease Implement this method")

	def fanart(self) -> Optional[str]:
		if 'fanart' in self._dict:
			return self._dict['fanart']
		else:
			return None

	def parse_country_studio(self) -> None:
		from vdlib.scrappers import countries
		if 'country_studio' in self._dict:
			parse_string = self._dict['country_studio']
			items = re.split(r'[/,|\(\);\\]', parse_string.replace(' - ', '/'))
			cntry = []
			stdio = []
			for s in items:
				s = s.strip()
				if len(s) == 0:
					continue
				cntry.append(s) if countries.isCountry(s) else stdio.append(s)
			self._dict['country'] = ', '.join(cntry)
			self._dict['studio'] = ', '.join(stdio)

	def __init__(self, full_title: str, content: str, settings = None):
		Informer.__init__(self)

		from bs4 import BeautifulSoup

		self._dict = dict()
		self._dict['full_title'] = full_title
		self.content = content
		html_doc = '<?xml version="1.0" encoding="UTF-8" ?>\n<html>' + content + '\n</html>'
		self.soup = BeautifulSoup(clean_html(html_doc), 'html.parser')
		self.settings = settings
		self.OK = self.parse()

	def make_filename(self) -> str:

		try:
			if 'imdb_id' in self._dict:
				return self.make_filename_imdb()
		except:
			pass

		title 			= self._dict.get('title', '')
		originaltitle 	= self._dict.get('originaltitle', '')
		year			= self._dict.get('year', '')

		return self.filename_with(title, originaltitle, year)

	def need_skipped(self, full_title: str) -> bool:

		for phrase in ['[EN]', '[EN / EN Sub]', '[Фильмография]', '[ISO]', 'DVD', 'стереопара', '[Season', 'Half-SBS']:
			if phrase in full_title:
				debug('Skipped by: ' + phrase)
				return True

			if re.search(r'\(\d\d\d\d[-/]', full_title):
				debug('Skipped by: Year')
				return True

		return False


def save_hashes(torrent_path: str) -> None:
	hashes_path = torrent_path + '.hashes'
	if filesystem.exists(torrent_path):
		tp = TorrentPlayer()
		tp.AddTorrent(torrent_path)
		td = tp.GetLastTorrentData()
		if td:
			info_hash = td['info_hash']

			if filesystem.exists(hashes_path):
				with filesystem.fopen(hashes_path, 'r') as rf:
					if info_hash in rf.read():
						return

			with filesystem.fopen(hashes_path, 'a+') as wf:
				wf.write(info_hash + '\n')

def get_true_filename(filename: Optional[str]) -> Optional[str]:
	if not filename or not isinstance(filename, str):
		return filename

	if filesystem.exists(filename):
		return filename

	parent_dir = filesystem.dirname(filename)
	parent_name = filesystem.basename(parent_dir)

	if not re.match(r'tt\d+', parent_name):
		return filename

	file_extension = os.path.splitext(filename)[1]
	for f in filesystem.listdir(parent_dir):
		if file_extension and f.endswith(file_extension):
			return filesystem.join(parent_dir, f)

	return filename
