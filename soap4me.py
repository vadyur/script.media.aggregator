import requests, feedparser, filesystem
from log import debug
from bs4 import BeautifulSoup

import json, urllib2

from base import DescriptionParserBase, Informer

class soap4me_data:
	api_token = None
	api_data = None


class DescriptionParser(DescriptionParserBase):
	def __init__(self, info, settings=None):
		Informer.__init__(self)
		self._dict.clear()

		api_info = (item for item in soap4me_data.api_data if item['title'] == info['originaltitle'] ).next()

		self.imdb_id = api_info['imdb_id']
		self.kp_id = api_info['kinopoisk_id']

		self.make_movie_api(self.imdb_id, self.kp_id)
		self.tvshow_api = TVShowAPI(info['originaltitle'], api_info['title_ru'], self.imdb_id, self.kp_id)

		api_title = tvshow_api.Title()
		self.tvshow_path = make_fullpath(api_title if api_title is not None else api_info['title_ru'], '')


def get_session(settings):
	s = requests.Session()

	login = s.post("https://soap4.me/login/", data = {"login": settings.soap4me_login, "password": settings.soap4me_password})

	debug('Login status: %d' % login.status_code)

	return s

def get_rss_url(session):
	dashboard = session.get('https://soap4.me/dashboard/')

	#print (dashboard.text)

	soup = BeautifulSoup(dashboard.text.encode('utf-8'), 'html.parser')

	div_rss = soup.find('div', class_ = 'rss')
	if div_rss:
		ul_list = div_rss.find('ul', class_='list')
		if ul_list:
			a = ul_list.find('a')
			if a:
				return a['href']

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


def write_episode(fulltitle, description, link, settings):
	return
	#tvshowapi.write_tvshow(fulltitle, link, settings, parser)


def write_twshow(info, settings):
	parser = DescriptionParser(info, settings)

	return parser


def write_tvshows(rss_url, path, settings):
	debug('------------------------- soap4me: %s -------------------------' % rss_url)

	shows = {}

	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(rss_url)

		cnt = 0
		settings.progress_dialog.update(0, 'soap4me', path)

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
				fulltitle=item.title,
				description=item.description,
				link=item.link,
				settings=settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'soap4me', path)


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
		write_tvshows(get_rss_url(session), settings.tvshow_path(), settings)
