import requests, feedparser, filesystem
from log import debug
from bs4 import BeautifulSoup

import json, urllib2

from base import DescriptionParserBase, Informer, make_fullpath
from tvshowapi import TVShowAPI


class soap4me_data:
	api_token = None
	api_data = None
	curr_sess = None


class DescriptionParser(DescriptionParserBase):
	def __init__(self, info, settings=None):
		Informer.__init__(self)
		self._dict = dict()

		self.api_info = None
		for item in soap4me_data.api_data:
			if item['title'] == info['originaltitle']:
				self.api_info = item
				break

		self.episodes_data = get_api_request('https://api.soap4.me/v2/episodes/' + str(self.api_info['sid']) + '/')

		from movieapi import KinopoiskAPI
		kp_url = KinopoiskAPI.make_url_by_id(self.kp_id)

		self.settings = settings

		self.make_movie_api(self.imdb_id, kp_url, self.settings)
		self.tvshow_api = TVShowAPI.get_by(info['originaltitle'], self.api_info['title_ru'], self.imdb_id, kp_url)

		self.OK = self.parse(self.api_info)

	@property
	def is_animation(self):
		return 'animation' in self.movie_api().imdbGenres().lower()

	@property
	def tvshow_path(self):
		api_title = self.tvshow_api.Title()
		return make_fullpath(api_title if api_title is not None else self.api_info['title_ru'], '')

	@property 
	def imdb_id(self):
		return self.api_info['imdb_id']

	@property
	def kp_id(self):
		return self.api_info['kinopoisk_id']

	@property
	def episode_runtime(self):
		return self.api_info[u'episode_runtime']

	@property
	def full_tvshow_path(self):
		path = self.settings.animation_tvshow_path() if self.is_animation else self.settings.tvshow_path()
		return filesystem.join(path, self.tvshow_path)

	def get_api_dict(self):
		return {
			u'title_ru': u'title',
			u'title': u'originaltitle',
			u'year': u'year',
			u'imdb_rating': u'rating',
			u'episode_runtime': u'runtime',
		}

	def get_tag(self, x):
		return {
			u'': u'genre',
			u'': u'director',
			u'': u'actor',
			u'': u'plot',
			u'': u'format',
			u'': u'country_studio',
			u'': u'video',
			u'': u'translate',
		}.get(x.strip(), u'')

	def parse(self, api_info):
		api_dict = self.get_api_dict()
		for key, value in api_dict.iteritems():
			self._dict[value] = api_info[key]

		self._dict['imdb_id'] = self.imdb_id
		self._dict['kp_id'] = self.kp_id

		self._dict['actor'] = self.movie_api().base_actors_list()

		return True

def get_session(settings):
	if soap4me_data.curr_sess:
		return soap4me_data.curr_sess

	s = requests.Session()

	login = s.post("https://soap4.me/login/", data = {"login": settings.soap4me_login, "password": settings.soap4me_password})

	debug('Login status: %d' % login.status_code)

	soap4me_data.curr_sess = s

	return s

def get_rss_url(session, settings):
	dashboard = session.get('https://soap4.me/dashboard/')

	#print (dashboard.text)

	soup = BeautifulSoup(dashboard.text.encode('utf-8'), 'html.parser')

	div_rss = soup.find('div', class_ = 'rss')
	if div_rss:
		ul_list = div_rss.find('ul', class_='list')
		if ul_list:
			aaa = ul_list.find_all('a')
			if len(aaa):
				try:
					ind = 0
					if '#' in settings.soap4me_rss:
						ind = int(settings.soap4me_rss.split('#')[1])
					a = aaa[ind]
					return a['href']
				except BaseException as e:
					debug(e)
					return aaa[0]['href']

	return None

def getInfoFromTitle(fulltitle):
	debug(fulltitle)
	parts = fulltitle.split('/')

	originaltitle = None
	season = None
	episode = None
	episode_name = None
	ozvuchka = None
	quality = None

	try:
		originaltitle = parts[0].strip()
		if originaltitle.startswith('['):
			originaltitle = originaltitle.split(']')[-1]
			originaltitle = originaltitle.strip()

		season_episode = parts[1].strip()

		import re
		m = re.match(r'.+?(\d+).+?(\d+)', season_episode)
		if m:
			season = int(m.group(1))
			episode = int(m.group(2))

		episode_name = parts[2].strip()
		detail = parts[3].strip()

		parts = detail.split(',')
		ozvuchka = parts[0].split(': ')[1]
		quality = parts[1].split(': ')[1]
	except BaseException as e:
		from log import print_tb
		print_tb(e)

	return {
		'originaltitle': originaltitle,
		'season': season,
		'episode': episode,
		'episode_name': episode_name,
		'ozvuchka': ozvuchka,
		'quality': quality
	}

class EpParser(DescriptionParser):
	def __init__(self, parser, info, torr_path, episode):
		self._dict = dict(parser.Dict())
		parts = []

		parts.append('AVC/H.264')

		if info['quality'].lower() == 'sd':
			parts.append('720x540')
		elif info['quality'].lower() == 'hd':
			parts.append('1280x720')
		elif info['quality'].lower() == 'fullhd':
			parts.append('1920x1080')

		from base import TorrentPlayer
		player = TorrentPlayer()
		player.AddTorrent(torr_path)
		data = player.GetLastTorrentData()
		if data:
			add_dict = self.get_add_data(data)
			if episode:
				seconds = int(parser.episode_runtime) * 60
				bitrate = add_dict['size'] * 8 / seconds
				parts.append(str(bitrate / 1000) + ' kbs')

		if parts:
			self._dict['video'] = ', '.join(parts)

	def get_add_data(self, data):
		for f in data['files']:
			return f


def write_episode(info, parser, fulltitle, description, link, settings):

	path = parser.full_tvshow_path
	season_path = 'Season ' + str(info['season'])

	with filesystem.save_make_chdir_context(filesystem.join(path, season_path)):
		from nfowriter import NFOWriter
		filename = '%02d. episode_s%02de%02d' % (info['episode'], info['season'], info['episode'])		

		episode = parser.tvshow_api.Episode(info['season'], info['episode'])
		if not episode:
			episode = {
				'title': info['episode_name'],
				'seasonNumber': info['season'],
				'episodeNumber': info['episode'],
				'image': '',
				'airDate': ''
						}

		NFOWriter(parser, tvshow_api=parser.tvshow_api, movie_api=parser.movie_api()).write_episode(episode, filename)
		from strmwriter import STRMWriter
	
		import re
		link = re.sub(r'/dl/[\d\w]+/', '/dl/', link)

		from downloader import TorrentDownloader
		dl = TorrentDownloader(link, settings.torrents_path(), settings)
		dl.download()

		path = filesystem.join(settings.torrents_path(), dl.get_subdir_name(),
							   dl.get_post_index() + '.torrent')

		STRMWriter(link).write(filename, settings=settings, parser=EpParser(parser, info, path, episode))


	#tvshowapi.write_tvshow(fulltitle, link, settings, parser)


def write_twshow(info, settings):
	parser = DescriptionParser(info, settings)

	with filesystem.save_make_chdir_context(parser.full_tvshow_path):
		from nfowriter import NFOWriter
		NFOWriter(parser, tvshow_api=parser.tvshow_api, movie_api=parser.movie_api()).write_tvshow_nfo()

	return parser


def write_tvshows(rss_url, settings):
	debug('------------------------- soap4me: %s -------------------------' % rss_url)

	shows = {}

	d = feedparser.parse(rss_url)

	cnt = 0
	settings.progress_dialog.update(0, 'soap4me', '')

	for item in d.entries:
		try:
			debug(item.title.encode('utf-8'))
		except:
			continue

		info = getInfoFromTitle(item.title)

		parser = None
		title = info['originaltitle']
		if not title in shows:
			parser = write_twshow(info, settings)
			shows[title] =  parser
		else:
			parser = shows[title]

		write_episode(
			info=info,
			parser=parser,
			fulltitle=item.title,
			description=item.description,
			link=item.link,
			settings=settings)

		cnt += 1
		settings.progress_dialog.update(cnt * 100 / len(d.entries), 'soap4me', '')


def get_api_token(settings):
	s = requests.Session()
	login = s.post("https://api.soap4.me/v2/auth/", data = {"login": settings.soap4me_login, "password": settings.soap4me_password})

	j = login.json()
	return j['token']


def get_api_request(url):
	headers = {'X-API-TOKEN': soap4me_data.api_token }
	resp = requests.post(url, headers=headers)	

	return resp.json()


def run(settings):
	session = get_session(settings)

	if soap4me_data.api_token is None:
		soap4me_data.api_token = get_api_token(settings)

	soap4me_data.api_data = get_api_request('https://api.soap4.me/v2/soap/')

	if settings.tvshows_save:
		write_tvshows(get_rss_url(session, settings), settings)

def page_for_season(show_title, ss, settings):
	url = 'https://soap4.me/soap/' + show_title.replace(' ', '_') + '/' + ss + '/'
	s = get_session(settings)

	r = s.get(url)
	return BeautifulSoup(r.text)

def search_generate(title, imdb, settings):
	soap4me_data.api_data = get_api_request('https://api.soap4.me/v2/soap/')

	tvshow = (item for item in soap4me_data.api_data if item['imdb_id'] == imdb).next()
	if tvshow:
		print tvshow
		info = {'originaltitle': tvshow['title']}
		parser = write_twshow(info, settings)

		seasons = {}

		for episode in parser.episodes_data['episodes']:
			info['season'] = int(episode['season'])
			info['episode'] = int(episode['episode'])
			info['episode_name'] = episode['title_ru']

			ss = str(info['season'])
			if ss not in seasons:
				seasons[ss] = page_for_season(tvshow['title'], ss, settings)

			li_s = seasons[ss].find_all('li', class_='ep', attrs={'data:episode': info['episode']})
			for li in li_s:
				link = 'https://soap4.me' + li.find('a')['href']
				info['quality'] = li.find('div', class_='quality').get_text().strip('\t\n ')
				info['ozvuchka'] = li.find('div', class_='translate').get_text().strip('\t\n ')
				write_episode(info, parser, '', '', link, settings)

	return 0


def download_torrent(url, path, settings):
	url = urllib2.unquote(url)
	debug('download_torrent:' + url)

	session = get_session(settings)
	r = session.get(url)
	with filesystem.fopen(path, 'wb') as torr:
		for chunk in r.iter_content(100000):
			torr.write(chunk)
	

	
