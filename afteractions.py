import xbmcvfs, xbmcaddon, os

_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)

class DoAction(object):
	def __init__(self, torrent_file, filename, nfo):
		copy_torrent 			= int(_addon.getSetting('torrent_files_action')) == 1
		download_files_action 	= int(_addon.getSetting('download_files_action'))
		download_files_path 	= _addon.getSetting('download_files_path')
		relative_path			= _addon.getSetting('storage_path')
		
		if copy_torrent:
			self.copy_torrent(torrent_file, nfo)
		
	def copy_torrent(self, torrent_file, nfo):
		torrents_dir 			= _addon.getSetting('torrent_files_path')
		dst 					= os.path.join(torrents_dir, nfo.replace('.nfo', '.torrent'))
		src						= torrent_file
		xbmcvfs.copy(src, dst)