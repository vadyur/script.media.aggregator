# -*- coding: utf-8 -*-
import log
from log import debug


import os, re, filesystem
from bs4 import BeautifulSoup
from settings import *
import urllib
from movieapi import *
import operator

KB = 1024
MB = KB * KB
GB = KB * MB

def make_fullpath(title, ext):
	return unicode(title.replace(':', '').replace('/', '#').replace('?', '').replace('"', "''") + ext)
	
def skipped(item):
	debug(item.title.encode('utf-8') + '\t\t\t[Skipped]')
	
def clean_html(page):
	#pattern = r"(?is)<script[^>]*>(.*?)</script>"
	#pattern = r'<script(.*?)</script>'
	#flags = re.M + re.S + re.I
	#r = re.compile(pattern, flags=flags)
	#debug(r)
	#page = r.sub('', page)
	#debug(page.encode('utf-8'))
	return page.replace("</sc'+'ript>", "").replace('</bo"+"dy>', '').replace('</ht"+"ml>', '')
	
def striphtml(data):
	p = re.compile(r'<.*?>')
	return p.sub('', data)

def get_rank(full_title, parser, settings):
	
	preffered_size = 7 * GB
	#preffered_resolution_h = 1920
	preffered_resolution_v = 1080 if settings.preffered_type == QulityType.Q1080 else 720
	preffered_bitrate	= settings.preffered_bitrate
	
	debug('preffered_type: %s' % settings.preffered_type)
	debug('preffered_bitrate: %d' % preffered_bitrate)
	
	rank = 0.0
	conditions = 0

	if 'seeds' in parser:
		seeds = parser['seeds']
		if seeds == 0:
			rank += 1000
		elif seeds < 5:
			rank += 1 + 3.0 / seeds
		else:
			rank += 1 + 1.0 / seeds
		conditions += 1
	else:
		rank += 1.5
		conditions += 1

		#parser = dict(parser, **info)

	if parser.get('gold', 'False') == 'True':
		rank += 0.8
		conditions += 1
		
	res_v = 1080
	if '720p' in full_title:
		res_v = 720
		
	if '2160p' in full_title:
		res_v = 2160
		
	if abs(preffered_resolution_v - res_v) > 0:
		rank += 2
		conditions += 1
		
	size = parser.get('size', '')
	if size != '':
		if int(size) > preffered_size:
			rank += int(size) / preffered_size
		else:
			rank += preffered_size / int(size)
		conditions += 1

	video = parser.get('video', '')
	for part in video.split(', '):
		multiplier = 0
		if 'kbps' in part \
			or 'kbs' in part \
			or 'Kbps' in part \
			or u'Кбит/сек' in part \
			or u'Кбит/с' in part \
			or 'Kb/s' in part \
			or '~' in part:
				multiplier = 1
		if 'mbps' in part \
			or 'mbs' in part \
			or 'Mbps' in part \
			or u'Мбит/сек' in part \
			or u'Mбит/с' in part \
			or u'Мбит/с' in part \
			or 'Mb/s' in part:
				multiplier = 1000
		if multiplier != 0:
			find = re.findall('[\d\.,]', part.split('(')[0])
			bitrate = ''.join(find).replace(',', '.')
			try:
				if bitrate != '' and float(bitrate) != 0 and float(bitrate) < 50000:
					debug('bitrate: %d kbps' % int(float(bitrate) * multiplier))
					if float(bitrate) * multiplier > preffered_bitrate:
						rank += float(bitrate) * multiplier / preffered_bitrate
					else:
						rank += preffered_bitrate / float(bitrate) * multiplier
					conditions += 1
				else:
					rank += 10
					conditions += 1
					debug('bitrate: not parsed')
			except:
				rank += 10
				conditions += 1
				debug('bitrate: not parsed')
		else:
			rank += 2
			conditions += 1
		
	if parser.get('format', '') == 'MKV':
		rank += 0.6
		conditions += 1
		
	if 'ISO' in parser.get('format', ''):
		rank += 100
		conditions += 1
	
	if conditions != 0:
		return rank / conditions
	else:
		return 1

def make_utf8(s):
	if isinstance(s, unicode):
		return s.encode('utf-8')
	return s

def seeds_peers(item):
	import player
	res = {}
	try:
		link = urllib.unquote(item['link'])
		settings = player.load_settings()
		if 'nnm-club' in link:
			debug('seeds_peers: ' + link)
			t_id = re.search(r't=(\d+)', link).group(1)
			fn = filesystem.join(settings.addon_data_path, 'nnmclub', t_id + '.stat')
			debug(fn)
			with filesystem.fopen(fn, 'r') as stat_file:
				import json
				res = json.load(stat_file)
				debug(str(res))
		elif 'hdclub' in link:
			t_id = re.search(r'\.php.+?id=(\d+)', link).group(1)
			fn = filesystem.join(settings.addon_data_path, 'hdclub', t_id + '.torrent')
			debug(fn)
			tp = TorrentPlayer()
			tp.AddTorrent(fn)
			data = tp.GetLastTorrentData()
			debug(str(data))
			if data:
				hashes = [data['info_hash']]
				import scraper
				res = scraper.scrape(data['announce'], hashes)
				debug(str(res))
				return res[data['info_hash']]

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
							if use_scrape_info:
								saved_dict['link'] = line.strip(u'\r\n\t ')
								sp = seeds_peers(saved_dict)
								saved_dict = dict(saved_dict, **sp)
							if 'rank' in saved_dict:
								curr_rank = float(saved_dict['rank'])
							else:
								curr_rank = get_rank(saved_dict['full_title'], saved_dict, settings)
						except:
							curr_rank = 1

						item = {'rank': curr_rank, 'link': line.strip(u'\r\n\t ')}
						items.append(dict(item, **saved_dict))
						saved_dict.clear()

		items.sort(key=operator.itemgetter('rank'))
		debug('Sorded items')
		debug(items)
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

class Informer(object):
	def __init__(self):
		self.__movie_api = None
		
	def make_movie_api(self, imdb_id, kp_id):
		self.__movie_api = MovieAPI(imdb_id, kp_id)
		
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
			originaltitle	= self.__movie_api['original_title']
			year			= self.__movie_api['release_date'].split('-')[0]
			
			return self.filename_with(title, originaltitle, year)
			
		return None
		
class DescriptionParserBase(Informer):
	_dict = {}

	def Dump(self):
		debug('-------------------------------------------------------------------------')
		for key, value in self._dict.iteritems():
			debug(key.encode('utf-8') + '\t: ' + value.encode('utf-8'))

	def Dict(self):
		return self._dict

	def get_value(self, tag):
		try:
			return self._dict[tag]
		except:
			return u''

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
		
		self._dict.clear()
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

	def Name(self, name):
		try:
			return name.decode('utf-8')
		except UnicodeDecodeError:
			import chardet
			enc = chardet.detect(name)
			debug('UnicodeDecodeError detected', log.lineno())
			# debug(enc['confidence'])
			# debug(enc['encoding'])
			if enc['confidence'] > 0.7:
				name = name.decode(enc['encoding'])
				debug(name)
				return name
			else:
				log.print_tb()

	def GetLastTorrentData(self):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")

		data = None
		with filesystem.fopen(self.path, 'rb') as torr:
			data = torr.read()

		if data is None:
			return None

		from bencode import BTFailure
		try:
			from bencode import bdecode
			decoded = bdecode(data)
		except BTFailure:
			debug("Can't decode torrent data (invalid torrent link?)")
			return None

		info = decoded['info']

		import hashlib
		from bencode import bencode
		self.info_hash = hashlib.sha1(bencode(info)).hexdigest()
		#debug(self.info_hash)

		playable_items = []
		try:
			if 'files' in info:
				for i, f in enumerate(info['files']):
					# debug(i)
					# debug(f)
					name = os.sep.join(f['path'])
					size = f['length']
					#debug(name)
					if TorrentPlayer.is_playable(name):
						playable_items.append({'index': i, 'name': self.Name(name), 'size': size})
			else:
				playable_items = [ {'index': 0, 'name': self.Name(info['name']), 'size': info['length'] } ]
		except UnicodeDecodeError:
			return None

		return { 'info_hash': self.info_hash, 'announce': decoded['announce'], 'files': playable_items }

	def StartBufferFile(self, fileIndex):
		raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		
	def CheckBufferComplete(self):
		raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		
	def GetBufferingProgress(self):
		raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		
	def GetStreamURL(self, playable_item):
		raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")