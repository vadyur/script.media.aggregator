# -*- coding: utf-8 -*-
from vdlib.util import filesystem

class QulityType:
	Q720 = '720p'
	Q1080 = '1080'
	Q2160 = '2160'

class CodecType:
	MPGSD = 'MPEG2/MPEG4 ASP'
	MPGHD = 'H264/AVC'
	MPGUHD = 'H265/HEVC'

class FakeProgressDlg(object):
	def update(self, *args):
		pass

_addon_name = '[COLOR=FF008000]Media[/COLOR] [COLOR=FFA0522D]Aggregator[/COLOR]'

class Settings(object):

	current_settings = None

	# единственный поддерживаемый движок
	torrent_player = 'TorrServer'

	def __init__(self, base_path,
	             movies_path			= 'Movies',
	             animation_path		= 'Animation',
	             documentary_path	= 'Documentary',
	             anime_path			= 'Anime',
	             anidub_login = '', anidub_password = '', anidub_rss=True, anidub_favorite=True,
	             nnmclub_login = '', nnmclub_password = '', nnmclub_pages = 1, nnmclub_hours=168, nnmclub_domain='nnmclub.to', nnmclub_use_ssl=True,
	             rutor_domain = 'rutor.info',
	             rutor_filter = 'CAMRip TS TC VHSRip TVRip SATRip IPTVRip HDTV HDTVRip WEBRip DVD5 DVD9 DVDRip Blu-Ray SuperTS SCR VHSScr DVDScr WP',
	             preffered_bitrate = 10000, preffered_type = QulityType.Q1080, preffered_codec = CodecType.MPGHD,
	             movies_save			= True,
	             animation_save		= True,
	             documentary_save	= True,
	             anime_save			= True,
	             tvshows_save		= True,
	             animation_tvshows_save = True,
	             torrent_path        = '',
	             addon_data_path	 = '',
	             rutor_nosd			= True):
		#--------------------------------------------------------------------------------
		Settings.current_settings	= self
		#--------------------------------------------------------------------------------
		self.__base_path			= filesystem.abspath(base_path)
		self.__movies_path 			= movies_path
		self.__animation_path 		= animation_path
		self.__documentary_path 	= documentary_path

		self.anidub_url				= 'https://tr.anidub.com/rss.xml'
		self.__anime_tvshow_path 	= anime_path
		self.anidub_login 			= anidub_login
		self.anidub_password 		= anidub_password
		self.anidub_rss 			= anidub_rss
		self.anidub_favorite 		= anidub_favorite

		self.nnmclub_domain			= nnmclub_domain
		self.nnmclub_use_ssl		= nnmclub_use_ssl
		self.nnmclub_login 			= nnmclub_login
		self.nnmclub_password 		= nnmclub_password
		self.nnmclub_pages			= nnmclub_pages
		self.nnmclub_hours			= nnmclub_hours

		self.show_sources			= False
		self.skip_show_sources		= False

		self.rutor_domain           = rutor_domain
		self.rutor_filter           = rutor_filter

		self.preffered_bitrate		= preffered_bitrate
		self.preffered_type			= preffered_type
		self.preffered_codec        = preffered_codec if preffered_codec else CodecType.MPGHD

		self.movies_save 			= movies_save
		self.animation_save 		= animation_save
		self.documentary_save 		= documentary_save
		self.anime_save 			= anime_save
		self.tvshows_save 			= tvshows_save
		self.animation_tvshows_save = animation_tvshows_save
		self.torrent_path           = torrent_path
		self.addon_data_path		= addon_data_path

		self.rutor_nosd				= rutor_nosd

		self.run_script				= False
		self.script_params			= ''
		self.remeber_watched		= False
		self.move_video				= False
		self.remove_files			= False
		self.copy_video_path		= ''
		self.copy_torrent			= False
		self.copy_torrent_path		= ''

		self.progress_dialog		= FakeProgressDlg()
		self.update_paths			= set()


	def __repr__(self):
		attrs = vars(self)
		result = ''
		for key, value in list(attrs.items()):
			if 'pass' in key:
				continue
			if result != '':
				result += '\n'
			key = key.replace('_Settings__', '')
			result += "%s: %s" % (key, value)
		return result

	@property
	def addon_name(self):
		return _addon_name

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

