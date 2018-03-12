# -*- coding: utf-8 -*-
import log
from log import debug


import os, re, filesystem
from settings import *
import urllib
from movieapi import *
import operator

KB = 1024
MB = KB * KB
GB = KB * MB

def lower(s):
	s = s.lower()
	_s = unicode()
	for ch in s:
		if ord(ch) >= ord(u'А') and ord(ch) <= ord(u'Я'):
			ofs = ord(u'а') - ord(u'А')
			_s += unichr(ord(ch) + ofs)
		else:
			_s += ch
	return _s

def make_fullpath(title, ext):
	if filesystem._is_abs_path(title):
		dir_path = filesystem.dirname(title)
		filename = filesystem.basename(title)
		pass
	else:
		dir_path = None
		filename = title

	if '/' in title:
		pass

	result = unicode(filename.replace(':', '').replace('/', '#').replace('?', '').replace('"', "''") + ext)
	if dir_path:
		result = filesystem.join(dir_path, result)

	return result

def skipped(item):
	debug(item.title.encode('utf-8') + '\t\t\t[Skipped]')

def remove_script_tags(file):
	pattern = re.compile(r'<script[\s\S]+?/script>')
	subst = ""
	return re.sub(pattern, subst, file)

def clean_html(page):
	#pattern = r"(?is)<script[^>]*>(.*?)</script>"
	#pattern = r'<script(.*?)</script>'
	#flags = re.M + re.S + re.I
	#r = re.compile(pattern, flags=flags)
	#debug(r)
	#page = r.sub('', page)
	#debug(page)
	page = remove_script_tags(page)

	return page.replace("</sc'+'ript>", "").replace('</bo"+"dy>', '').replace('</ht"+"ml>', '')


def striphtml(data):
	p = re.compile(r'<.*?>')
	return p.sub('', data)


def detect_mpg(str_detect):
	try:
		str_detect = str_detect.lower()
		return 'divx' in str_detect or 'xvid' in str_detect or 'mpeg2' in str_detect or 'mpeg-2' in str_detect
	except:
		return False


def detect_h264(str_detect):
	try:
		str_detect = str_detect.lower()
		return 'avc' in str_detect or 'h264' in str_detect or 'h.264' in str_detect
	except:
		return False


def detect_h265(str_detect):
	try:
		str_detect = str_detect.lower()
		return 'hevc' in str_detect or 'h265' in str_detect or 'h.265' in str_detect
	except:
		return False

def is_torrent_remembed(parser, settings):
	from downloader import TorrentDownloader
	import urllib
	link = parser.get('link').split('torrent=')[-1]
	if link:
		torr_downloader = TorrentDownloader(urllib.unquote(link), None, settings)
		path = filesystem.join(settings.torrents_path(), torr_downloader.get_subdir_name(), torr_downloader.get_post_index() + '.choice')
		return filesystem.exists(path)

	return False


def get_rank(full_title, parser, settings):

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
	mults = []

	if '[ad]' in full_title.lower():
		mults.append(1.1)

	if 'seeds' in parser:
		seeds = parser['seeds']
		if seeds == 0:
			mults.append(10)
		else:
			v = 1.0 + 0.25 / seeds
			mults.append(v)
	else:
		mults.append(1.25)

	#if parser.get('gold', 'False') == 'True':
	#	rank += 0.8
	#	conditions += 1

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

	#if len(parts) == 0:
	#	rank += 2
	#	conditions += 1

	for part in parts:
		multiplier = 0
		if 'kbps' in part \
			or 'kbs' in part \
			or 'Kbps' in part \
			or u'Кбит/сек' in part \
			or u'Кбит/с' in part \
			or 'Kb/s' in part:
				multiplier = 1
		if 'mbps' in part \
			or 'mbs' in part \
			or 'Mbps' in part \
			or u'Мбит/сек' in part \
			or u'Mбит/с' in part \
			or u'Мбит/с' in part \
			or 'Mb/s' in part \
			or 'mb/s' in part:
				multiplier = 1000
		if multiplier != 0:
			find = re.findall('[\d\.,]', part.split('(')[0])
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


def make_utf8(s):
	if isinstance(s, unicode):
		return s.encode('utf-8')
	return s

def scrape_now(fn):
	debug(fn)
	with filesystem.fopen(fn, 'r') as fin:
		from bencode import BTFailure
		try:
			from bencode import bdecode
			decoded = bdecode(fin.read())
		except BTFailure:
			debug("Can't decode torrent data (invalid torrent link?)")
			return {}

		info = decoded['info']

		import hashlib
		from bencode import bencode
		info_hash = hashlib.sha1(bencode(info)).hexdigest()

		hashes = [info_hash]
		import scraper

		result = []
		threads = []

		def start_scrape(announce):
			def do_scrape():
				try:
					res = scraper.scrape(announce, hashes, 0.25)
					result.append(res[info_hash])
				except:
					debug(announce + ' - not working')
					pass

			import threading			
			t = threading.Thread(target=do_scrape)
			threads.append(t)
			t.start()

		if 'announce-list' in decoded:
			for announce in decoded['announce-list']:
				start_scrape(announce[0])

			alive = True
			while not result and alive:
				alive = False
				for t in threads:
					if t.is_alive():
						alive = True
						break
		elif 'announce' in decoded:
			res = scraper.scrape(decoded['announce'], hashes)
			return res[info_hash]


		if result:
			return result[0]

	return {}


def seeds_peers(item):
	res = {}
	try:
		link = urllib.unquote(item['link'])
		try:
			import player
			settings = player.load_settings()
		except:
			settings = Settings.current_settings
		if 'nnm-club' in link:
			debug('seeds_peers: ' + link)
			t_id = re.search(r't=(\d+)', link).group(1)
			fn = filesystem.join(settings.torrents_path(), 'nnmclub', t_id + '.stat')
			debug(fn)
			with filesystem.fopen(fn, 'r') as stat_file:
				import json
				res = json.load(stat_file)
				debug(str(res))
		elif 'hdclub' in link:
			t_id = re.search(r'\.php.+?id=(\d+)', link).group(1)
			fn = filesystem.join(settings.torrents_path(), 'elitehd', t_id + '.torrent')
			return scrape_now(fn)
		elif 'bluebird' in link:
			t_id = re.search(r'\.php.+?id=(\d+)', link).group(1)
			fn = filesystem.join(settings.torrents_path(), 'bluebird', t_id + '.torrent')
			if not filesystem.exists(fn):
				import bluebird
				bluebird.download_torrent(link, fn, settings)
			return scrape_now(fn)
		elif 'rutor' in link:
			t_id = re.search(r'/torrent/(\d+)', link).group(1)
			fn = filesystem.join(settings.torrents_path(), 'rutor', t_id + '.torrent')
			return scrape_now(fn)
		elif 'kinohd'  in link:
			part = self.url.split('/')[-1]
			t_id = re.search(r'^(\d+)', part).group(1)
			fn = filesystem.join(settings.torrents_path(), 'kinohd', t_id + '.torrent')
			return scrape_now(fn)

	except BaseException as e:
		debug(str(e))
	return res


class STRMWriterBase(object):
	def make_alternative(self, strmFilename, link, parser):
		strmFilename_alt = strmFilename + '.alternative'

		s_alt = u''
		if filesystem.isfile(strmFilename_alt):
			with filesystem.fopen(strmFilename_alt, "r") as alternative:
				s_alt = alternative.read().decode('utf-8')

		if not (link in s_alt):
			try:
				with filesystem.fopen(strmFilename_alt, "a+") as alternative:
					for key, value in parser.Dict().iteritems():
						if key in ['director', 'studio', 'country', 'plot', 'actor', 'genre', 'country_studio']:
							continue
						alternative.write('#%s=%s\n' % (make_utf8(key), make_utf8(value)))
					alternative.write(link.encode('utf-8') + '\n')
			except:
				pass


	@staticmethod
	def get_links_with_ranks(strmFilename, settings, use_scrape_info = False):
		#import vsdbg
		#vsdbg._bp()

		strmFilename_alt = strmFilename + '.alternative'
		items = []
		saved_dict = {}
		if filesystem.isfile(strmFilename_alt):
			with filesystem.fopen(strmFilename_alt, "r") as alternative:
				curr_rank = 1
				while True:
					line = alternative.readline()
					if not line:
						break
					line = line.decode('utf-8')
					if line.startswith('#'):
						line = line.lstrip('#')
						parts = line.split('=')
						if len(parts) > 1:
							saved_dict[parts[0]] = parts[1].strip(' \n\t\r')
					elif line.startswith('plugin://script.media.aggregator'):
						try:
							saved_dict['link'] = line.strip(u'\r\n\t ')
							if use_scrape_info:
								sp = seeds_peers(saved_dict)
								saved_dict = dict(saved_dict, **sp)
							if 'rank' in saved_dict:
								curr_rank = float(saved_dict['rank'])
							else:
								curr_rank = get_rank(saved_dict.get('full_title', ''), saved_dict, settings)
						except BaseException as e:
							import log
							log.print_tb(e)
							curr_rank = 1

						item = {'rank': curr_rank, 'link': line.strip(u'\r\n\t ')}
						items.append(dict(item, **saved_dict))
						saved_dict.clear()

		items.sort(key=operator.itemgetter('rank'))
		#debug('Sorded items')
		#debug(items)
		return items


	@staticmethod
	def get_link_with_min_rank(strmFilename, settings):
		items = STRMWriterBase.get_links_with_ranks(strmFilename, settings)

		if len(items) == 0:
			return None
		else:
			return items[0]['link']

	@staticmethod
	def has_link(strmFilename, link):
		strmFilename_alt = strmFilename + '.alternative'
		if filesystem.isfile(strmFilename_alt):
			with filesystem.fopen(strmFilename_alt, "r") as alternative:
				for line in alternative:
					if line.startswith('plugin://'):
						if link in urllib.unquote(line):
							return True
		return False

	@staticmethod
	def write_alternative(strmFilename, links_with_ranks):
		strmFilename_alt = strmFilename + '.alternative'
		with filesystem.fopen(strmFilename_alt, 'w') as alternative:
			for variant in links_with_ranks:
				if 'link' in variant:
					for k, v in variant.iteritems():
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

	def make_movie_api(self, imdb_id, kp_id, settings):
		orig=None
		year=None
		#imdbRaiting=None

		if not imdb_id:
			if u'originaltitle' in self.Dict():
				orig = self.Dict()['originaltitle']
			if u'year' in self.Dict():
				year = self.Dict()['year']

		from movieapi import MovieAPI
		self.__movie_api, imdb_id = MovieAPI.get_by(imdb_id=imdb_id, kinopoisk_url=kp_id, orig=orig, year=year, settings=settings)
		if imdb_id:
			self.Dict()['imdb_id'] = imdb_id

	def movie_api(self):
		return self.__movie_api

	def filename_with(self, title, originaltitle, year):
		if title == originaltitle:
			filename = title
		elif title == '' and originaltitle != '':
			filename = originaltitle
		elif title != '' and originaltitle == '':
			filename = title
		else:
			filename = title + ' # ' + originaltitle

		if year != None or year != '' or year != 0:
			filename += ' (' + str(year) + ')'

		return filename

	def make_filename_imdb(self):
		if self.__movie_api:
			title 			= self.__movie_api['title']
			originaltitle	= self.__movie_api['originaltitle']
			year			= self.__movie_api['year']

			return self.filename_with(title, originaltitle, year)

		return None

class DescriptionParserBase(Informer):
	_dict = {}

	def Dump(self):
		debug('-------------------------------------------------------------------------')
		for key, value in self._dict.iteritems():
			debug(key + '\t: ' + value)

	def Dict(self):
		return self._dict

	def get_value(self, tag, def_value=u''):
		try:
			return self._dict[tag]
		except:
			return def_value

	def get(self, tag, def_value):
		return self._dict.get(tag, def_value)

	def parsed(self):
		return self.OK

	def parse(self):
		raise NotImplementedError("def parse(self): not imlemented.\nPlease Implement this method")

	def fanart(self):
		if 'fanart' in self._dict:
			return self._dict['fanart']
		else:
			return None

	def parse_country_studio(self):
		import countries
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

	def __init__(self, full_title, content, settings = None):
		Informer.__init__(self)

		from bs4 import BeautifulSoup

		self._dict = dict()
		self._dict['full_title'] = full_title
		self.content = content
		html_doc = '<?xml version="1.0" encoding="UTF-8" ?>\n<html>' + content.encode('utf-8') + '\n</html>'
		self.soup = BeautifulSoup(clean_html(html_doc), 'html.parser')
		self.settings = settings
		self.OK = self.parse()

	def make_filename(self):

		try:
			if 'imdb_id' in self._dict:
				return self.make_filename_imdb()
		except:
			pass

		title 			= self._dict.get('title', '')
		originaltitle 	= self._dict.get('originaltitle', '')
		year			= self._dict.get('year', '')

		return self.filename_with(title, originaltitle, year)
		#return filename

	def need_skipped(self, full_title):

		for phrase in [u'[EN]', u'[EN / EN Sub]', u'[Фильмография]', u'[ISO]', u'DVD', u'стереопара', u'[Season', u'Half-SBS']:
			if phrase in full_title:
				debug('Skipped by: ' + phrase.encode('utf-8'))
				return True


			if re.search('\(\d\d\d\d[-/]', full_title.encode('utf-8')):
				debug('Skipped by: Year')
				return True

		return False

class TorrentPlayer(object):

	def __init__(self):
		self._decoded	= None
		self._info_hash = None

	@property
	def decoded(self):
		if not self._decoded:
			data = None
			with filesystem.fopen(self.path, 'rb') as torr:
				data = torr.read()

			if data is None:
				return None

			from bencode import BTFailure
			try:
				from bencode import bdecode
				self._decoded = bdecode(data)
			except BTFailure:
				debug("Can't decode torrent data (invalid torrent link?)")
				return None

		return self._decoded

	@property
	def info_hash(self):
		if not self._info_hash:
			try:
				import hashlib
				from bencode import bencode
				info = self.decoded['info']
				self._info_hash = hashlib.sha1(bencode(info)).hexdigest()
			except:
				return None

		return self._info_hash

	@staticmethod
	def is_playable(name):
		filename, file_extension = os.path.splitext(name)
		return file_extension in ['.mkv', '.mp4', '.ts', '.avi', '.m2ts', '.mov']

	def AddTorrent(self, path):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		self.path = path

	def CheckTorrentAdded(self):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		return filesystem.exists(self.path)

	def updateCheckingProgress(self, progressBar):
		pass

	@staticmethod
	def Name(name):
		try:
			return name.decode('utf-8')
		except UnicodeDecodeError:
			try:
				import chardet
				enc = chardet.detect(name)
				log.debug('confidence: {0}'.format(enc['confidence']))
				log.debug('encoding: {0}'.format(enc['encoding']))
				if enc['confidence'] > 0.5:
					try:
						name = name.decode(enc['encoding'])
					except UnicodeDecodeError:
						pass
				else:
					import vsdbg
					#vsdbg._bp()
					log.print_tb()
			except BaseException as e:
				import vsdbg
				#vsdbg._bp()
				log.print_tb()
				
		return name

	def GetLastTorrentData(self):

		decoded =self.decoded
		info = decoded['info']

		def info_name():
			if 'name.utf-8' in info:
				return info['name.utf-8']
			else:
				return info['name']

		def f_path(f):
			if 'path.utf-8' in f:
				return f['path.utf-8']
			else:
				return f['path']

		name = '.'
		playable_items = []
		try:
			if 'files' in info:
				for i, f in enumerate(info['files']):
					# debug(i)
					# debug(f)
					name = os.sep.join(f_path(f))
					size = f['length']
					#debug(name)
					if TorrentPlayer.is_playable(name):
						playable_items.append({'index': i, 'name': TorrentPlayer.Name(name), 'size': size})
					name = TorrentPlayer.Name(info_name())
			else:
				playable_items = [ {'index': 0, 'name': TorrentPlayer.Name(info_name()), 'size': info['length'] } ]
		except UnicodeDecodeError:
			return None

		return { 'info_hash': self.info_hash, 'announce': decoded['announce'], 'files': playable_items, 'name': name }

	def GetTorrentInfo(self):
		try:
			return { 'downloaded' : 	100,
			            'size' : 		100,
			            'dl_speed' : 	1,
			            'ul_speed' :	0,
			            'num_seeds' :	1,
			            'num_peers' :	0
			            }
		except:
			pass

		return None

	def StartBufferFile(self, fileIndex):
		pass

	def CheckBufferComplete(self):
		pass

	def GetBufferingProgress(self):
		pass

	def GetStreamURL(self, playable_item):
		pass

	def updateDialogInfo(self, progress, progressBar):
		pass

	def GetBufferingProgress(self):
		return 100

	def CheckBufferComplete(self):
		return True

	def loop(self):
		pass

def save_hashes(torrent_path):
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
