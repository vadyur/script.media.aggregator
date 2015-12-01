# -*- coding: utf-8 -*-
import os

class Settings:
	# feed=dl&
	
	base_url 			= 'http://hdclub.org/rss.php'
	
	def __init__(self, base_path, hdclub_passkey = '', anidub_login = '', anidub_password = ''):
		self.movies_url 			= self.base_url + '?cat=71&passkey=' + hdclub_passkey
		self.animation_url 			= self.base_url + '?cat=70&passkey=' + hdclub_passkey
		self.documentary_url 		= self.base_url + '?cat=78&passkey=' + hdclub_passkey
		
		self.__base_path			= os.path.abspath(base_path).decode('utf-8')
		self.__movies_path 			= u'Movies'
		self.__animation_path 		= u'Animation'
		self.__documentary_path 	= u'Documentary'
	
		self.anidub_url				= 'http://tr.anidub.com/rss.xml'
		self.__anime_tvshow_path 	= u'Anime'
		self.anidub_login 			= anidub_login
		self.anidub_password 		= anidub_password
		
	def __repr__(self):
		attrs = vars(self)
		#return ', \n'.join("%s: %s" % item for item in attrs.items() )
		return ''
	
	def base_path(self):
		return self.__base_path.decode('utf-8')
	def movies_path(self):
		return os.path.join(self.__base_path, self.__movies_path).decode('utf-8')
	def animation_path(self):
		return os.path.join(self.__base_path, self.__animation_path).decode('utf-8')
	def documentary_path(self):
		return os.path.join(self.__base_path, self.__documentary_path).decode('utf-8')
	def anime_tvshow_path(self):
		return os.path.join(self.__base_path, self.__anime_tvshow_path).decode('utf-8')
		
		
