import os

class Settings:
	# feed=dl&
	
	base_url 			= 'http://hdclub.org/rss.php'
	
	def __init__(self, base_path, hdclub_passkey = '', anidub_login = '', anidub_password = ''):
		self.movies_url 			= self.base_url + '?cat=71&passkey=' + hdclub_passkey
		self.animation_url 			= self.base_url + '?cat=70&passkey=' + hdclub_passkey
		self.documentary_url 		= self.base_url + '?cat=78&passkey=' + hdclub_passkey
		
		self.base_path				= base_path
		self.__movies_path 			= 'Movies'
		self.__animation_path 		= 'Animation'
		self.__documentary_path 	= 'Documentary'
	
		self.anidub_url				= 'http://tr.anidub.com/rss.xml'
		self.__anime_tvshow_path 	= 'Anime'
		self.anidub_login 			= anidub_login
		self.anidub_password 		= anidub_password
		
	def __repr__(self):
		attrs = vars(self)
		return ', \n'.join("%s: %s" % item for item in attrs.items())
	
	def movies_path(self):
		return os.path.join(self.base_path, self.__movies_path)
	def animation_path(self):
		return os.path.join(self.base_path, self.__animation_path)
	def documentary_path(self):
		return os.path.join(self.base_path, self.__documentary_path)
	def anime_tvshow_path(self):
		return os.path.join(self.base_path, self.__anime_tvshow_path)
		