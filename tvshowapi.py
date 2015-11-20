import urllib2, json

class TVShowAPI(object):
	
	myshows = None
	myshows_ep = None
	
	def __init__(self, title, ruTitle):
		base_url = 'http://api.myshows.me/shows/search/?q='
		url = base_url + urllib2.quote(title.encode('utf-8'))
		self.myshows = json.load(urllib2.urlopen(url))
		if not self.valid():
			url = base_url + urllib2.quote(ruTitle.encode('utf-8'))
			self.myshows = json.load(urllib2.urlopen(url))

		if self.valid():
			print url
			id = self.get_myshows_id()
			print id
			if id != 0:
				url = 'http://api.myshows.me/shows/' + str(id)
				self.myshows_ep = json.load(urllib2.urlopen(url))
				if self.valid_ep():
					print url
			
		print str(self.valid())
		print str(self.valid_ep())
		
	def get_myshows_id(self):
		try:
			if self.valid():
				for key in self.myshows.keys():
					return self.myshows[key]['id']
		except:
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
				