# -*- coding: utf-8 -*-
import os, filesystem

class QulityType:
	Q720p = '720p'
	Q1080 = '1080'
	
class TorrentPlayer:
	YATP 		= 'YATP'
	TORR2HTTP	= 'torrent2http'

class FakeProgressDlg(object):
	def update(self, *args):
		pass

class Settings:
	# feed=dl&
	
	base_url 			= 'http://hdclub.org/rss.php'
	
	def __init__(self, base_path, 
		movies_path			= u'Movies',
		animation_path		= u'Animation',
		documentary_path	= u'Documentary',
		anime_path			= u'Anime',
		hdclub_passkey 		= '', 
		anidub_login = '', anidub_password = '', 
		nnmclub_login = '', nnmclub_password = '', nnmclub_pages = 1, nnmclub_hours=168,
		rutor_domain = 'rutor.info',
		preffered_bitrate = 10000, preffered_type = QulityType.Q1080,
		torrent_player = TorrentPlayer.YATP, storage_path = '',
		movies_save			= True,
		animation_save		= True,
		documentary_save	= True,
		anime_save			= True,
		tvshows_save		= True,
		animation_tvshows_save = True,
		torrent_path        = ''):
		#--------------------------------------------------------------------------------
		self.movies_url 			= self.base_url + '?cat=71&passkey=' + hdclub_passkey
		self.animation_url 			= self.base_url + '?cat=70&passkey=' + hdclub_passkey
		self.documentary_url 		= self.base_url + '?cat=78&passkey=' + hdclub_passkey
		self.hdclub_passkey			= hdclub_passkey
		
		self.__base_path			= filesystem.abspath(base_path)
		self.__movies_path 			= movies_path
		self.__animation_path 		= animation_path
		self.__documentary_path 	= documentary_path
	
		self.anidub_url				= 'http://tr.anidub.com/rss.xml'
		self.__anime_tvshow_path 	= anime_path
		self.anidub_login 			= anidub_login
		self.anidub_password 		= anidub_password

		self.nnmclub_login 			= nnmclub_login
		self.nnmclub_password 		= nnmclub_password
		self.nnmclub_pages			= nnmclub_pages
		self.nnmclub_hours			= nnmclub_hours
		self.use_kinopoisk			= True

		self.rutor_domain           = rutor_domain
		
		self.preffered_bitrate		= preffered_bitrate
		self.preffered_type			= preffered_type
		
		self.torrent_player 		= torrent_player
		self.storage_path			= storage_path
		
		self.movies_save 			= movies_save
		self.animation_save 		= animation_save
		self.documentary_save 		= documentary_save
		self.anime_save 			= anime_save
		self.tvshows_save 			= tvshows_save
		self.animation_tvshows_save = animation_tvshows_save
		self.torrent_path           = torrent_path
		
		self.progress_dialog		= FakeProgressDlg()
		
	def __repr__(self):
		attrs = vars(self)
		#return ', \n'.join("%s: %s" % item for item in attrs.items() )
		result = ''
		for key, value in attrs.items():
			if 'pass' in key:
				continue
			if result != '':
				result += '\n'
			key = key.replace('_Settings__', '')
			result += "%s: %s" % (key, value)
		return result
	
	def base_path(self):
		return self.__base_path

	def movies_path(self):
		return filesystem.join(self.__base_path, self.__movies_path)

	def animation_path(self):
		return filesystem.join(self.__base_path, self.__animation_path)

	def documentary_path(self):
		return filesystem.join(self.__base_path, self.__documentary_path)

	def anime_tvshow_path(self):
		return filesystem.join(self.__base_path, self.__anime_tvshow_path)

	def animation_tvshow_path(self):
		return filesystem.join(self.__base_path, 'Animation TVShows')

	def tvshow_path(self):
		return filesystem.join(self.__base_path, 'TVShows')

	def torrents_path(self):
		return self.torrent_path if self.torrent_path else self.addon_data_path

