from base import *
from bencode import bdecode, BTFailure


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

	urls = ['s(\d+)e(\d+)', '(\d+)[x|-](\d+)', 'E(\d+)', 'Ep(\d+)', '\((\d+)\)']
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
			if my_episode and my_episode > 365: my_episode = None
			debug('[FileNamesPrepare] ' + '%d %d %s' % (my_season, my_episode, filename))
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


def parse_torrent(data, season=None):
	try:
		decoded = bdecode(data)
	except BTFailure:
		print "Can't decode torrent data (invalid torrent link? %s)" % link
		return

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

	files = []
	for item in get_list(dirlist):
		if item is not None:
			files.append({'name': item[2], 'season': season if season is not None else item[0], 'episode': item[1]})
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


def test(link):
	import requests
	r = requests.get(link)
	if r.status_code == requests.codes.ok:
		files = parse_torrent(r.content)


class TVShowAPI(object):
	myshows = None
	myshows_ep = None

	def __init__(self, title, ruTitle, imdbId=None):
		if imdbId:
			print imdbId
			try:
				imdbId = int(re.search('(\d+)', imdbId).group(1))
				print imdbId
			except:
				imdbId = None

		base_url = 'http://api.myshows.me/shows/search/?q='
		url = base_url + urllib2.quote(title.encode('utf-8'))
		self.myshows = json.load(urllib2.urlopen(url))
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
