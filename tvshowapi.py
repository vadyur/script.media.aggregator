import json
import re
import urllib2
from contextlib import closing
from zipfile import ZipFile, BadZipfile, LargeZipFile
import xml.etree.ElementTree as ET

import io

import filesystem
from base import TorrentPlayer, make_fullpath, get_rank


def debug(s):
	try:
		if isinstance(s, unicode):
			print s.encode('utf-8')
		else:
			print s

	except:
		pass


def cutStr(s):
	return s.replace('.', ' ').replace('_', ' ').replace('[', ' ').replace(']', ' ').lower().strip()


def sweetpair(l):
	from difflib import SequenceMatcher

	s = SequenceMatcher()
	ratio = []
	for i in range(0, len(l)): ratio.append(0)
	for i in range(0, len(l)):
		for p in range(0, len(l)):
			s.set_seqs(l[i], l[p])
			ratio[i] = ratio[i] + s.quick_ratio()
	id1, id2 = 0, 0
	for i in range(0, len(l)):
		if ratio[id1] <= ratio[i] and i != id2 or id2 == id1 and ratio[id1] == ratio[i]:
			id2 = id1
			id1 = i
		# debug('1 - %d %d' % (id1, id2))
		elif (ratio[id2] <= ratio[i] or id1 == id2) and i != id1:
			id2 = i
		# debug('2 - %d %d' % (id1, id2))

	debug('[sweetpair]: id1 ' + l[id1] + ':' + str(ratio[id1]))
	debug('[sweetpair]: id2 ' + l[id2] + ':' + str(ratio[id2]))

	return [l[id1], l[id2]]


def sortext(filelist):
	result = {}
	for name in filelist:
		ext = name.split('.')[-1]
		try:
			result[ext] = result[ext] + 1
		except:
			result[ext] = 1
	lol = result.iteritems()
	lol = sorted(lol, key=lambda x: x[1])
	debug('[sortext]: lol:' + str(lol))
	popext = lol[-1][0]
	result, i = [], 0
	for name in filelist:
		if name.split('.')[-1] == popext:
			result.append(name)
			i = i + 1
	result = sweetpair(result)
	debug('[sortext]: result:' + str(result))
	return result


def cutFileNames(l):
	from difflib import Differ

	d = Differ()

	text = sortext(l)
	newl = []
	for li in l: newl.append(cutStr(li[0:len(li) - 1 - len(li.split('.')[-1])]))
	l = newl

	text1 = cutStr(text[0][0:len(text[0]) - 1 - len(text[0].split('.')[-1])])
	text2 = cutStr(text[1][0:len(text[1]) - 1 - len(text[1].split('.')[-1])])
	sep_file = " "
	result = list(d.compare(text1.split(sep_file), text2.split(sep_file)))
	debug('[cutFileNames] ' + unicode(result))

	start = ''
	end = ''

	for res in result:
		if str(res).startswith('-') or str(res).startswith('+') or str(res).startswith('.?'):
			break
		start = start + str(res).strip() + sep_file
	result.reverse()
	for res in result:
		if str(res).startswith('-') or str(res).startswith('+') or str(res).startswith('?'):
			break
		end = sep_file + str(res).strip() + end

	newl = l
	l = []
	debug('[cutFileNames] [start] ' + start)
	debug('[cutFileNames] [end] ' + end)
	for fl in newl:
		if cutStr(fl[0:len(start)]) == cutStr(start): fl = fl[len(start):]
		if cutStr(fl[len(fl) - len(end):]) == cutStr(end): fl = fl[0:len(fl) - len(end)]
		try:
			isinstance(int(fl.split(sep_file)[0]), int)
			fl = fl.split(sep_file)[0]
		except:
			pass
		l.append(fl)
	debug('[cutFileNames] [sorted l]  ' + unicode(sorted(l, key=lambda x: x)))
	return l


def FileNamesPrepare(filename):
	my_season = None
	my_episode = None

	try:
		if int(filename):
			my_episode = int(filename)
			debug('[FileNamesPrepare] ' + str([my_season, my_episode, filename]))
			return [my_season, my_episode, filename]
	except:
		pass

	urls = [r's(\d+)e(\d+)', r's(\d+) e(\d+)', r'(\d+)[x|-](\d+)', r'E(\d+)', r'Ep(\d+)', r'\((\d+)\)']
	for file in urls:
		match = re.compile(file, re.DOTALL | re.I | re.IGNORECASE).findall(filename)
		if match:
			try:
				my_episode = int(match[1])
				my_season = int(match[0])
			except:
				try:
					my_episode = int(match[0])
				except:
					try:
						my_episode = int(match[0][1])
						my_season = int(match[0][0])
					except:
						try:
							my_episode = int(match[0][0])
						except:
							break
			if my_season and my_season > 100: my_season = None
			if my_episode:
				if my_episode > 1000:
					dm = divmod(my_episode, 100)
					if dm[0] + 1 == dm[1]:
						my_episode = dm[0]
					else:
						my_episode = None
				elif my_episode > 365:
					my_episode = None
			try:
				debug('[FileNamesPrepare] ' + '%d %d %s' % (my_season, my_episode, filename))
			except TypeError:
				debug('[FileNamesPrepare]: TypeError')
				debug('[FileNamesPrepare] ' + str([my_season, my_episode, filename]))
				pass
			return [my_season, my_episode, filename]


def get_list(dirlist):
	files = []
	if len(dirlist) > 1:
		cutlist = cutFileNames(dirlist)
	else:
		cutlist = dirlist
	for fn in cutlist:
		x = FileNamesPrepare(fn)
		files.append(x)

	return files


def seasonfromname(name):
	match = re.compile('(\d+)', re.I).findall(name)
	if match:
		try:
			num = int(match[0])
			return num if num > 0 and num < 20 else None
		except:
			pass
	return None


def parse_torrent(data, season=None):
	from bencode import BTFailure
	try:
		from bencode import bdecode
		decoded = bdecode(data)
	except BTFailure:
		print "Can't decode torrent data (invalid torrent link?)"
		return []

	info = decoded['info']
	dirlist = []
	parent_list = []
	if 'files' in info:
		for i, f in enumerate(info['files']):
			# print i
			# print f
			fname = f['path'][-1]
			print fname
			if TorrentPlayer.is_playable(fname):
				dirlist.append(fname)  # .decode('utf-8').encode('cp1251')

	save_season = season
	files = []
	for item in get_list(dirlist):
		if item is not None:
			if season is None:
				if item[0] is None:
					season = seasonfromname(info['name'])
					if season is None:
						f_item = next((f for f in info['files'] if item[2] in f['path'][-1]), None )
						try:
							season = seasonfromname(f_item['path'][-2])
						except:
							pass
				else:
					season = item[0]
			files.append({'name': item[2], 'season': season, 'episode': item[1]})
			season = save_season
		else:
			# TODO
			continue

	files.sort(key=lambda x: (x['season'], x['episode']))
	return files


def parse_torrent2(data):
	try:
		decoded = bdecode(data)
	except BTFailure:
		print "Can't decode torrent data (invalid torrent link? %s)" % link
		return

	files = []
	info = decoded['info']
	if 'files' in info:
		for i, f in enumerate(info['files']):
			# print i
			# print f
			fname = f['path'][-1]
			if TorrentPlayer.is_playable(fname):
				s = re.search('s(\d+)e(\d+)[\._ ]', fname, re.I)
				if s:
					season = int(s.group(1))
					episode = int(s.group(2))
					print 'Filename: %s\t index: %d\t season: %d\t episode: %d' % (fname, i, season, episode)
					files.append({'index': i, 'name': fname, 'season': season, 'episode': episode})

	if len(files) == 0:
		return

	files.sort(key=lambda x: (x['season'], x['episode']))
	return files

def season_from_title(fulltitle):
	parts = re.split(r'[,;\(\)\[\]]', fulltitle)
	for part in parts:
		if u'сезонов' in part.lower():
			return None
		if u'сезоны' in part.lower():
			return None
		if u'сезон' in part.lower():
			if re.search('\d+\D+\d+', part):
				return None
			match = re.search('(\d+)', part)
			if match:
				return int(match.group(1))

	return None


def write_tvshow(fulltitle, link, settings, parser):
	from nfowriter import NFOWriter
	from strmwriter import STRMWriter
	import requests

	r = requests.get(link)
	if r.status_code == requests.codes.ok:
		files = parse_torrent(r.content, season_from_title(fulltitle))

		title = parser.get_value('title')
		print title.encode('utf-8')
		originaltitle = parser.get_value('originaltitle')
		print originaltitle.encode('utf-8')

		tvshow_path = make_fullpath(title, '')
		print tvshow_path.encode('utf-8')

		try:
			save_path = filesystem.save_make_chdir(tvshow_path)

			imdb_id = parser.get('imdb_id', None)

			tvshow_api = TVShowAPI(originaltitle, title, imdb_id)
			NFOWriter(parser, tvshow_api=tvshow_api, movie_api=parser.movie_api()).write_tvshow_nfo()

			prevSeason = None
			episodes = None
			cnt = 0
			for f in files:
				cnt += 1
				try:
					new_season = prevSeason != f['season']
					if new_season:
						episodes = tvshow_api.episodes(f['season'])

					results = filter(lambda x: x['episodeNumber'] == f['episode'], episodes)
					episode = results[0] if len(results) > 0 else None
					if episode is None:
						episode = {
							'title': title,
							'seasonNumber': f['season'],
							'episodeNumber': f['episode'],
							'image': '',
							'airDate': ''
						}

					season_path = 'Season %d' % f['season']
				except:
					continue

				try:
					tvshow_full_path = filesystem.getcwd()
					filesystem.save_make_chdir(season_path)

					results = filter(lambda x: x['season'] == f['season'] and x['episode'] == f['episode'], files)
					if len(results) > 1:	# Has duplicate episodes
						filename = f['name']
					else:
						try:
							filename = '%02d. episode_s%02de%02d' % (cnt, f['season'], f['episode'])
						except BaseException as e:
							print e
							filename = f['name']

					try:
						print filename
						filename = filename.decode('utf-8')
					except:
						print [filename]

					STRMWriter(parser.link()).write(filename, cutname=f['name'], settings=settings, parser=parser)
					NFOWriter(parser, tvshow_api=tvshow_api, movie_api=parser.movie_api()).write_episode(episode, filename)

					prevSeason = f['season']

				finally:
					filesystem.chdir(tvshow_full_path)
		finally:
			filesystem.chdir(save_path)


def test(link):
	import requests
	r = requests.get(link)
	if r.status_code == requests.codes.ok:
		files = parse_torrent(r.content)


# TheTVDB
# 1. http://thetvdb.com/api/GetSeriesByRemoteID.php?imdbid=ttxxxxxxx&language=ru	id=<Data><Series><id>
# 2. http://thetvdb.com/api/1D62F2F90030C444/series/<id>/all/ru.zip					zip -> banners.xml, actors.xml, ru.xml

class TheTVDBAPI(object):
	__base_url = 'http://thetvdb.com/api/'
	__apikey = '1D62F2F90030C444'
	__lang = 'ru'
	def __init__(self, imdbId):
		self.tvdb = None
		try:
			response1 = urllib2.urlopen(self.__base_url + 'GetSeriesByRemoteID.php?imdbid=%s&language=%s' % (imdbId, self.__lang) )
			try:
				self.thetvdbid = re.search('<id>(\d+)</id>', response1.read()).group(1)
			except AttributeError:
				return
		except urllib2.HTTPError as e:
			print 'TheTVDBAPI: ' + str(e)
			return

		url2 = self.__base_url + self.__apikey + '/series/%s/all/%s.zip' % (self.thetvdbid, self.__lang)
		print url2

		response2 = urllib2.urlopen(url2)
		try:
			f = io.BytesIO(response2.read())
			with closing(ZipFile(f, 'r')) as zf:
				with closing(zf.open('banners.xml', 'r')) as banners:
					self.tvdb = ET.fromstring(banners.read())
					'''
					for banner in self.tvdb:
						for child in banner:
							print [child.tag, child.text]
					'''
		except BadZipfile as bz:
			print str(bz)
		except LargeZipFile as lz:
			print str(lz)
		# else:
		#	print 'Unknown'


	def getArt(self, type):
		result = []
		if self.tvdb is None:
			return result

		baseurl = 'http://thetvdb.com/banners/'
		for banner in self.tvdb:
			BannerType = banner.find('BannerType')
			if BannerType is not None:
				if BannerType.text == type:
					BannerPath = banner.find('BannerPath')
					ThumbnailPath = banner.find('ThumbnailPath')

					if BannerPath is not None and ThumbnailPath is not None:
						result.append({'path': baseurl + BannerPath.text, 'thumb': baseurl + ThumbnailPath.text})
		return result

	def Fanart(self):
		return self.getArt('fanart')

	def Poster(self):
		return self.getArt('poster')

class TVShowAPI(object):
	myshows = None
	myshows_ep = None

	def __init__(self, title, ruTitle, imdbId=None):

		if imdbId:
			self.tvdb = TheTVDBAPI(imdbId)
			print imdbId
			try:
				imdbId = int(re.search('(\d+)', imdbId).group(1))
				print imdbId
			except:
				imdbId = None
		else:
			self.tvdb = None

		base_url = 'http://api.myshows.me/shows/search/?q='
		url = base_url + urllib2.quote(title.encode('utf-8'))
		try:
			self.myshows = json.load(urllib2.urlopen(url))
		except urllib2.HTTPError as e:
			print 'TVShowAPI: ' + str(e)
			return

		if not self.valid():
			url = base_url + urllib2.quote(ruTitle.encode('utf-8'))
			self.myshows = json.load(urllib2.urlopen(url))

		if self.valid():
			print url
			# print unicode(json.dumps(self.myshows, sort_keys=True, indent=4, separators=(',', ': ')), 'unicode-escape').encode('utf-8')
			id = self.get_myshows_id(imdbId)
			print id
			if id != 0:
				url = 'http://api.myshows.me/shows/' + str(id)
				self.myshows_ep = json.load(urllib2.urlopen(url))
				if self.valid_ep():
					print url

		print str(self.valid())
		print str(self.valid_ep())

	def get_myshows_id(self, imdbId):
		# try:
		if True:
			if self.valid():
				for key in self.myshows.keys():
					print key
					section = self.myshows[str(key)]
					if imdbId:
						if section['imdbId'] == imdbId:
							return section['id']
					else:
						return section['id']
		else:
			# except:
			pass

		return 0

	def valid(self):
		if self.myshows != None:
			return len(self.myshows) > 0
		else:
			return False

	def valid_ep(self):
		if self.myshows_ep != None:
			return len(self.myshows_ep) > 0
		else:
			return False

	def data(self):
		if self.valid_ep():
			return self.myshows_ep

		if self.valid():
			for key in self.myshows.keys():
				return key

		return None

	def episodes(self, season):
		episodes__ = []
		if self.valid_ep():
			for episode in self.myshows_ep['episodes']:
				ep = self.myshows_ep['episodes'][episode]
				if ep['seasonNumber'] == season and ep['episodeNumber'] != 0:
					episodes__.append(ep)

		return sorted(episodes__, key=lambda k: k['episodeNumber'])

	def Fanart(self):
		if self.tvdb is None:
			return []
		else:
			return self.tvdb.getArt('fanart')

	def Poster(self):
		if self.tvdb is None:
			return []
		else:
			return self.tvdb.getArt('poster')

