# -*- coding: utf-8 -*-

import os, re
from settings import Settings
from base import *
from nfowriter import *
from strmwriter import *
import requests


_RSS_URL = 'http://nnm-club.me/forum/rss-topic.xml'
_BASE_URL = 'http://nnm-club.me/forum/'
_HD_PORTAL_URL = _BASE_URL + 'portal.php?c=11'
_NEXT_PAGE_SUFFIX='&start='
_ITEMS_ON_PAGE=15

class DescriptionParser(DescriptionParserBase):
	
	def __init__(self, content):
		self.content = content
		self.OK = self.parse()
		
	def get_tag(self, x):
		return {
			#u'Название:': u'title',
			#u'Оригинальное название:': u'originaltitle',
			#u'Год выхода:': u'year',
			u'Жанр:': u'genre',
			u'Режиссер:': u'director',
			u'Актеры:': u'actor',
			u'Описание:': u'plot',
			u'Продолжительность:': u'runtime',
			u'Качество видео:': u'format',
			u'Производство:' : u'country_studio',
			u'Видео:': u'video',
		}.get(x.strip(), u'')
		
	def clean(self, title):
		return title
		
	def get_title(self, full_title):
		try:
			found = re.search('^(.+?) /', full_title).group(1)
			return self.clean( found)
		except AttributeError:
			return full_title
	
	def get_original_title(self, full_title):
		try:
			found = re.search('^.+? / (.+) \(', full_title).group(1)
			return self.clean(found)
		except AttributeError:
			return full_title
			
	def get_year(self, full_title):
		try:
			found = re.search('\(([0-9]+)\)', full_title).group(1)
			return unicode(found)
		except AttributeError:
			return 0
			
	def make_filename(self):
		try:
			filename = self.dict['title'] + ' # ' + self.dict['originaltitle'] 
			filename += ' (' + self.dict['year'] + ')'
		finally:
			return filename

		
	def parse(self):
		for a in self.content.select('.substr a.pgenmed'):
			self.__link = _BASE_URL + a['href']
			print self.__link

			full_title = a.get_text()
			print 'full_title: ' + full_title.encode('utf-8')
			if '[EN]' in full_title:
				return False
						
			self.dict['full_title'] = full_title
			self.dict['title'] = self.get_title(full_title)
			self.dict['originaltitle'] = self.get_original_title(full_title)
			self.dict['year'] = self.get_year(full_title)
			
			fname = make_fullpath(self.make_filename(), '.strm')
			if STRMWriterBase.has_link(fname, self.__link):
				print 'Skipped'
				return False
			
			r = requests.get(self.__link)
			if r.status_code == requests.codes.ok:
				self.soup = BeautifulSoup(r.text, 'html.parser')
				
				tag = u''
				self.dict['gold'] = False
				for a in self.soup.select('img[src="images/gold.gif"]'):
					self.dict['gold'] = True
					print 'gold'
				
				for span in self.soup.select('span.postbody span'):
					try:
						text = span.get_text()
						tag = self.get_tag(text)
						if tag != '':
							if tag != u'plot':
								self.dict[tag] = unicode(span.next_sibling).strip()
							else:
								self.dict[tag] = unicode(span.next_sibling.next_sibling).strip()
							print self.dict[tag].encode('utf-8')
					except: pass
						
				for a in self.soup.select('#imdb_id'):
					try:
						href = a['href']
						components = href.split('/')
						if components[2] == u'www.imdb.com' and components[3] == u'title':
							self.dict['imdb_id'] = components[4]
					except:
						pass

				for img in self.soup.select('img.postImg'):
					try:
						self.dict['thumbnail'] = img['src']
						print self.dict['thumbnail']
					except:
						pass
				
				if 'country_studio' in self.dict:
					parse_string = self.dict['country_studio']
					parts = parse_string.split(' / ')
					self.dict['country'] = parts[0]
					if len(parts) > 1:
						self.dict['studio'] = parts[1]
				
				return True
		return False
		
	def link(self):
		return self.__link


class PostsEnumerator(object):		
	#==============================================================================================
	__items = []
	
	def __init__(self):
		self.__s = requests.Session()

	def process_page(self, url):
		request = self.__s.get(url)
		self.soup = BeautifulSoup(request.text, 'html.parser')
		print url
		
		for tbl in self.soup.select('table.pline'):
			self.__items.append(tbl)
		
	def items(self):
		return self.__items

def write_movies(content, path, settings):
	
	original_dir = os.getcwd()
	
	if not os.path.exists(path):
		os.makedirs(path)
		
	os.chdir(path)
	# ---------------------------------------------
	enumerator = PostsEnumerator()
	for i in range(settings.nnmclub_pages):
		enumerator.process_page(_HD_PORTAL_URL + _NEXT_PAGE_SUFFIX + str(i * _ITEMS_ON_PAGE))

	for post in enumerator.items():
		parser = DescriptionParser(post)
		if parser.parsed():
			filename = parser.make_filename()
			if filename == '':
				continue
			print filename.encode('utf-8')
			STRMWriter(parser.link()).write(filename, rank = get_rank(parser.get_value('full_title'), parser), settings = settings)
			NFOWriter().write(parser, filename)

		
	# ---------------------------------------------
	os.chdir(original_dir)


def run(settings):
	write_movies(_HD_PORTAL_URL, settings.movies_path(), settings)
	
def get_magnet_link(url):
	r = requests.get(url)
	if r.status_code == requests.codes.ok:
		soup = BeautifulSoup(r.text, 'html.parser')
		for a in soup.select('a[href*="magnet:"]'):
			print a['href']
			return a['href']
	return None
	
def download_torrent(url, path, settings):
	url = urllib2.unquote(url)
	print 'download_torrent:' + url
	s = requests.Session()
	
	r = s.get("http://nnm-club.me/forum/login.php")
	#with open('log-get.html', 'w+') as f:
	#	f.write(r.text.encode('cp1251'))
	
	soup = BeautifulSoup(r.text, 'html.parser')
	
	for inp in soup.select('input[name="code"]'):
		code = inp['value']
		print code
	
	data = {"username": settings.nnmclub_login, "password": settings.nnmclub_password, 
																"autologin": "on", "code": code, "redirect": "", "login": "" }
	login = s.post("http://nnm-club.me/forum/login.php", data = data, headers={'Referer': "http://nnm-club.me/forum/login.php"})
	#with open('log-post.html', 'w+') as f:
	#	f.write(login.text.encode('cp1251'))
		
	#print login.headers
	print 'Login status: %d' % login.status_code
	
	#print login.text.encode('cp1251')
	
	page = s.get(url)
	#print page.text.encode('cp1251')
	
	soup = BeautifulSoup(page.text, 'html.parser')
	a = soup.select('td.gensmall > span.genmed > b > a')
	if len(a) > 0:
		href = 'http://nnm-club.me/forum/' + a[0]['href']
		print s.headers
		r = s.get(href, headers={'Referer': url})
		print r.headers
		try:
			with open(path, 'wb') as torr:
				for chunk in r.iter_content(100000):
					torr.write(chunk)
			return True
		except: 
			pass

	return False
	

if __name__ == '__main__':
	settings = Settings('../media_library', nnmclub_pages = 1)
	run(settings)
	
