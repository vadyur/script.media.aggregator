# coding: utf-8

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
		self.dict.clear()
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
			parts = title.split(u'ТВ-')
			if len(parts) == 1:
				parts = title.split(u'TV-')
			if len(parts) > 1:
				found = re.search('([0-9]+)', parts[1]).group(1)
				self.dict['season'] = int(found)
		except:
			pass
	
	#==============================================================================================
	def get_episodes_num(self, full_title):
		try:
			found = re.search(' \[([0-9]+) ', full_title).group(1)
			return int(found)
		except AttributeError:
			return 1
		
	#==============================================================================================
	def parse(self):
		tag = u''
		self.dict['gold'] = False
		self.dict['season'] = 1
		
		for title in self.soup.select('#news-title'):
			full_title = title.get_text()
			print full_title.encode('utf-8')
			self.dict['title'] = self.get_title(full_title)
			self.dict['originaltitle'] = self.get_original_title(full_title)
			self.parse_season_from_title(full_title)
			self.dict['episodes'] = self.get_episodes_num(full_title)
		
		for b in self.soup.select('div.xfinfodata b'):
			try:
				text = b.get_text()
				tag = self.get_tag(text)
				if tag != '':
					span = b.find_next_sibling('span')
					self.dict[tag] = span.get_text().strip()
			except:
				pass
				
		for div in self.soup.select('div.story_c'):
			try:
				text = div.get_text()
				text = text.split(u'Описание:')[1]
				text = text.split(u'Эпизоды')[0]
				text = text.split(u'Скриншоты')[0]
				text = text.strip()
				self.dict['plot'] = text
				#print '---'
				#print text.encode('utf-8')
				#print '---'
			except:
				pass
				
		for b in self.soup.select('div.story_h .rcol sup b'):
			try:
				text = b.get_text()
				text = text.split(' ')[0]
				self.dict['rating'] = float(text) * 2
				print 'rating: ' + str(self.dict['rating'])
			except:
				pass
				
		for img in self.soup.select('span.poster img'):
			try:
				self.dict['thumbnail'] = img['src'].strip()
				print self.dict['thumbnail']
			except:
				pass
				
		fanart = []
		for a in self.soup.select('ul.clr li a'):
			try:
				print a['href']
				fanart.append(a['href'].strip())
			except:
				pass
		if len(fanart) != 0:
			self.dict['fanart'] = fanart
			
		for img in self.soup.select('div.video_info a img'):
			try:
				self.dict['studio'] = img['alt'].strip()
				print self.dict['studio']
			except:
				pass
				
		return True


###################################################################################################
def write_tvshow_nfo(parser, tvshow_api):
	print filesystem.getcwd().encode('utf-8')
	NFOWriter().write(parser, 'tvshow', 'tvshow', tvshow_api)
	return

###################################################################################################
def write_tvshow(content, path, settings):
	original_dir = filesystem.getcwd()
	
	if not filesystem.exists(path):
		filesystem.makedirs(path)
		
	filesystem.chdir(path)
	
	d = feedparser.parse(content)
	
	for item in d.entries:
		print '-------------------------------------------------------------------------'
		print item.link
		parser = DescriptionParser(item.link)
		
		if parser.parsed():
			title = parser.get_value('title')
			print title.encode('utf-8')
			originaltitle = parser.get_value('originaltitle')
			print originaltitle.encode('utf-8')
			season = parser.get_value('season')
			filename = title
			
			print 'Episodes: ' + str(parser.get_value('episodes'))
			
			save_path = filesystem.getcwd()
			
			tvshow_path = make_fullpath(title, '')
			print tvshow_path.encode('utf-8')
			
			if not filesystem.exists(tvshow_path):
				filesystem.makedirs(tvshow_path)
			
			filesystem.chdir(tvshow_path)
			
			tvshow_api = TVShowAPI(originaltitle, title)
			write_tvshow_nfo(parser, tvshow_api)
			filesystem.chdir(save_path)
			
			season_path = filesystem.join(make_fullpath(title, u''), u'Season ' + unicode(season))
			print season_path.encode('utf-8')
			if not filesystem.exists(season_path):
				filesystem.makedirs(season_path)

			filesystem.chdir(season_path)
				
			episodes = tvshow_api.episodes(season)
			for episode in episodes:
				title 			= episode['title']
				shortName 		= episode['shortName']
				episodeNumber	= episode['episodeNumber']
				
				if episodeNumber <= parser.get_value('episodes'):
					filename = str(episodeNumber) + '. ' + 'episode_' + shortName
					print filename.encode('utf-8')
					
					STRMWriter(item.link).write(filename, episodeNumber, settings = settings)
					NFOWriter().write_episode(episode, filename, tvshow_api)
				
			filesystem.chdir(save_path)
		else:
			skipped(item)
			
		del parser
			
	filesystem.chdir(original_dir)
	
def download_torrent(url, path, settings):
	url = urllib2.unquote(url)
	print 'download_torrent:' + url
	s = requests.Session()
	login = s.post("http://tr.anidub.com/", data = {"login_name": settings.anidub_login, "login_password": settings.anidub_password, "login": "submit"})
	print 'Login status: %d' % login.status_code
	
	page = s.get(url)
	#print page.text.encode('utf-8')
	soup = BeautifulSoup(page.text, 'html.parser')
	a = soup.select('#tv720 div.torrent_h a')
	if len(a) > 0:
		href = 'http://tr.anidub.com' + a[0]['href']
		print s.headers
		r = s.get(href, headers={'Referer': url})
		print r.headers
		
		# 'Content-Type': 'application/x-bittorrent'
		if 'Content-Type' in r.headers:
			if not 'torrent' in r.headers['Content-Type']:
				return False
		
		try:
			with filesystem.fopen(path, 'wb') as torr:
				for chunk in r.iter_content(100000):
					torr.write(chunk)
			return True
		except: 
			pass
	return False

###################################################################################################
def run(settings):
	write_tvshow(settings.anidub_url, settings.anime_tvshow_path(), settings)

