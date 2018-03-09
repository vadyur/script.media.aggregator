# coding: utf-8
import log
from log import debug


from settings import Settings
from base import *
import feedparser, urllib2, re
from bs4 import BeautifulSoup
from nfowriter import *
from strmwriter import *
import requests, filesystem

###################################################################################################
class DescriptionParser(DescriptionParserBase):
	#==============================================================================================
	def get_content(self, url):
		page = urllib2.urlopen(url)
		return page
	
	#==============================================================================================
	def __init__(self, url):
		Informer.__init__(self)
		
		self._dict = dict()
		self.content = self.get_content(url)
		#html_doc = '<?xml version="1.0" encoding="UTF-8" ?>\n<html>' + content.encode('utf-8') + '\n</html>'
		self.soup = BeautifulSoup(self.content, 'html.parser')
		self.OK = self.parse()
				
	#==============================================================================================
	def get_tag(self, x):
		return {
			u'Год: ': u'year',
			u'Жанр: ': u'genre',
			u'Описание: ': u'plot',
			u'Режиссер: ': u'director',
			u'Продолжительность: ': u'runtime',
			u'Страна: ': u'country',
		}.get(x, u'')
		
	#==============================================================================================
	def clean(self, title):
		try:
			title = title.split(u' ТВ-')[0]
			title = title.split(u' TV-')[0]
			title = title.split(u' [')[0]
		except:
			pass
		return title.strip()
	
	#==============================================================================================	
	def get_title(self, full_title):
		try:
			found = re.search('^(.+?) /', full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title
	
	#==============================================================================================	
	def get_original_title(self, full_title):
		try:
			found = re.search('^.+? / (.+)', full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title
	
	#==============================================================================================
	def parse_season_from_title(self, title):
		try:
			found = re.search(r"(\d) \[\d+\D+\d+\]", title)
			if found:
				try:
					self._dict['season'] = int(found.group(1))
					return
				except:
					pass

			parts = title.split(u'ТВ-')
			if len(parts) == 1:
				parts = title.split(u'TV-')
			if len(parts) > 1:
				found = re.search('([0-9]+)', parts[1]).group(1)
				self._dict['season'] = int(found)
		except:
			pass
	
	#==============================================================================================
	def get_episodes_num(self, full_title):
		try:
			found = re.search(' \[([0-9]+) ', full_title).group(1)
			return int(found)
		except AttributeError:
			return 1

	def date_added_duration(self):
		ul = self.soup.find('ul', class_='story_inf')
		if ul:
			for li in ul.find_all('li'):
				txt = li.get_text()
				parts = txt.split(':')
				if len(parts) > 1 and parts[0] == u'Дата':
					date, t = parts[1].split(',')	# 		d	u' 30-09-2012'	unicode

					from datetime import datetime, timedelta

					day = timedelta(1)
					yesterday = datetime.today() - day

					#date = ' 30-09-2012'

					if u'Сегодня' in date:
						d = datetime.today()
					elif u'Вчера' in date:
						d = yesterday
					else:
						try:
							d = datetime.strptime(date.strip(), '%d-%m-%Y')
						except TypeError:
							d = datetime.today()

					dt = datetime.today() - d
					return dt
		
	#==============================================================================================
	def parse(self):
		tag = u''
		self._dict['gold'] = False
		self._dict['season'] = 1
		
		for title in self.soup.select('#news-title'):
			full_title = title.get_text()
			debug(full_title)
			self._dict['title'] = self.get_title(full_title)
			self._dict['originaltitle'] = self.get_original_title(full_title)
			self.parse_season_from_title(full_title)
			self._dict['episodes'] = self.get_episodes_num(full_title)
		
		for b in self.soup.select('div.xfinfodata b'):
			try:
				text = b.get_text()
				tag = self.get_tag(text)
				if tag != '':
					span = b.find_next_sibling('span')
					self._dict[tag] = span.get_text().strip()
			except:
				pass
				
		for div in self.soup.select('div.story_c'):
			try:
				text = div.get_text()
				text = text.split(u'Описание:')[1]
				text = text.split(u'Эпизоды')[0]
				text = text.split(u'Скриншоты')[0]
				text = text.strip()
				self._dict['plot'] = text
				#debug('---')
				#debug(text)
				#debug('---')
			except:
				pass
				
		for b in self.soup.select('div.story_h .rcol sup b'):
			try:
				text = b.get_text()
				text = text.split(' ')[0]
				self._dict['rating'] = float(text) * 2
				debug('rating: ' + str(self._dict['rating']))
			except:
				pass
				
		for img in self.soup.select('span.poster img'):
			try:
				self._dict['thumbnail'] = img['src'].strip()
				debug(self._dict['thumbnail'])
			except:
				pass
				
		fanart = []
		for a in self.soup.select('ul.clr li a'):
			try:
				debug(a['href'])
				fanart.append(a['href'].strip())
			except:
				pass

		if len(fanart) != 0:
			self._dict['fanart'] = fanart
		else:
			dt = self.date_added_duration()
			if dt and dt.days <= 14:
				return False
			
		for img in self.soup.select('div.video_info a img'):
			try:
				self._dict['studio'] = img['alt'].strip()
				debug(self._dict['studio'])
			except:
				pass

		tags = []
		for a in self.soup.select('a[href*="https://tr.anidub.com/tags/"]'):
			tags.append(a.get_text().strip())
		if len(tags) > 0:
			self._dict['tag'] = tags

				
		return True

###################################################################################################
def write_tvshow_nfo(parser, tvshow_api, tvshow_path):
	try:
		if write_tvshow_nfo.favorites:
			parser.Dict().get('tag', []).append('favorites')
	except:
		pass

	NFOWriter(parser, tvshow_api=tvshow_api).write_tvshow_nfo(tvshow_path)
	return

###################################################################################################
def write_tvshow(content, path, settings):
	with filesystem.save_make_chdir_context(path):
		d = feedparser.parse(content)

		cnt = 0
		settings.progress_dialog.update(0, 'anidub', path)

		for item in d.entries:
			write_tvshow_item(item, path, settings)

			cnt += 1
			settings.progress_dialog.update(cnt * 100 / len(d.entries), 'anidub', path)


def write_tvshow_item(item, path, settings, path_out=[]):
	debug('-------------------------------------------------------------------------')
	debug(item.link)
	parser = DescriptionParser(item.link)
	if parser.parsed():
		title = parser.get_value('title')
		debug(title)
		originaltitle = parser.get_value('originaltitle')
		debug(originaltitle)
		season = parser.get_value('season')

		from downloader import TorrentDownloader
		TorrentDownloader(item.link, settings.torrents_path(), settings).download()

		debug('Episodes: ' + str(parser.get_value('episodes')))

		tvshow_path = make_fullpath(title, '')

		tvshow_path = filesystem.join(path, tvshow_path)
		debug(tvshow_path)

		path_out.append(tvshow_path)

		with filesystem.save_make_chdir_context(tvshow_path):
			tvshow_api = TVShowAPI.get_by(originaltitle, title)
			write_tvshow_nfo(parser, tvshow_api, tvshow_path)

		season_path = filesystem.join(tvshow_path, u'Season ' + unicode(season))
		debug(season_path)

		with filesystem.save_make_chdir_context(season_path):

			episodes = tvshow_api.episodes(season)

			if len(episodes) < parser.get_value('episodes'):
				for i in range(len(episodes) + 1, parser.get_value('episodes') + 1):
					episodes.append({
						'title': title,
						'showtitle': title,
						'short': 's%02de%02d' % (season, i),
						'episode': i,
						'season': season
					})

			for episode in episodes:
				title = episode['title']
				shortName = episode['short']
				episodeNumber = episode['episode']

				if episodeNumber <= parser.get_value('episodes'):
					filename = str(episodeNumber) + '. ' + 'episode_' + shortName
					debug(filename)

					ep = tvshow_api.Episode(season, episodeNumber)
					if ep:
						episode = ep

					STRMWriter(item.link).write(filename, season_path, episodeNumber=episodeNumber, settings=settings)
					NFOWriter(parser, tvshow_api=tvshow_api).write_episode(episode, filename, season_path)

	else:
		skipped(item)
	del parser


def get_session(settings):
	s = requests.Session()
	data = {"login_name": settings.anidub_login, "login_password": settings.anidub_password, "login": "submit"}
	headers = {
		'Host':							'tr.anidub.com',
		'Origin':						'https://tr.anidub.com',
		'Referer':						'https://tr.anidub.com/',
		'Upgrade-Insecure-Requests':	'1',
		'User-Agent':					'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132'
	}
	login = s.post("https://tr.anidub.com/", data=data, headers=headers)
	debug('Login status: %d' % login.status_code)
	if 'login_name' in login.content:
		debug('Login failed')

	return s
	
def download_torrent(url, path, settings):
	from base import save_hashes
	save_hashes(path)

	url = urllib2.unquote(url)
	debug('download_torrent:' + url)

	s = get_session(settings)

	page = s.get(url)
	#debug(page.text.encode('utf-8'))
	soup = BeautifulSoup(page.text, 'html.parser')

	try:
	    a = soup.select_one('#tv720 div.torrent_h a')
	except TypeError:
		a = None

	try:
		if a is None:
			a = soup.select_one('div.torrent_h > a')
	except TypeError:
		a = None

	if a is not None:
		href = 'https://tr.anidub.com' + a['href']
		debug(s.headers)
		r = s.get(href, headers={'Referer': url})
		debug(r.headers)
		
		if 'Content-Type' in r.headers:
			if not 'torrent' in r.headers['Content-Type']:
				return False
		
		try:
			with filesystem.fopen(path, 'wb') as torr:
				for chunk in r.iter_content(100000):
					torr.write(chunk)
			save_hashes(path)
			return True
		except: 
			pass

	return False

def write_pages(url, path, settings, params={}, filter_fn=None, dialog_title = None, path_out=[]):
	s = get_session(settings)
	if params:
		page = s.post(url, data=params)
	else:
		page = s.get(url)
	soup = BeautifulSoup(page.content, 'html.parser')
	page_no = 1

	cnt = 0
	
	class Item:
		def __init__(self, link, title):
			self.link = link
			self.title = title
	
	with filesystem.save_make_chdir_context(path):
		while True:
			if params:
				selector = soup.select('div.search_post > div.text > h2 > a')
			else:
				selector = soup.select('article.story > div.story_h > div.lcol > h2 > a')

			if not selector:
				break
	
			settings.progress_dialog.update(0, dialog_title, path)
	
			for a in selector:
				log.debug(a['href'])
				link = a['href']
				title = a.get_text()
				if filter_fn and filter_fn(title):
					continue

				write_tvshow_item(Item(link, title), path, settings, path_out)
	
				cnt += 1
				settings.progress_dialog.update(cnt * 100 / len(selector), dialog_title, path)

			if not 'favorites' in url:
				break
	
			page_no += 1
			page = s.get(url + 'page/%d/' % page_no)
	
			if page.status_code == requests.codes.ok:
				soup = BeautifulSoup(page.text, 'html.parser')
			else:
				break

	return cnt


def write_favorites(path, settings):
	write_pages('https://tr.anidub.com/favorites/', path, settings, dialog_title=u'Избранное AniDUB')


def search_generate(what, settings, path_out):
	def filter(title):
		if what not in title:
			return True

		return False

	write_tvshow_nfo.favorites = False
	return write_pages('https://tr.anidub.com/index.php?do=search', 
				settings.anime_tvshow_path(), settings, 
				{'do': 'search',
				'subaction': 'search',
				'story': what.encode('utf-8')}, filter,
				dialog_title=u'Поиск AniDUB',
				path_out=path_out)
	

###################################################################################################
def run(settings):
	if settings.anime_save:
		if settings.anidub_rss:
			write_tvshow_nfo.favorites = False
			write_tvshow(settings.anidub_url, settings.anime_tvshow_path(), settings)
		if settings.anidub_favorite:
			write_tvshow_nfo.favorites = True
			write_favorites(settings.anime_tvshow_path(), settings)


if __name__ == '__main__':
	settings = Settings('../media_library')
	run(settings)
