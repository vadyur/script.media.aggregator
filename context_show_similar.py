from log import debug

def show_similar():
	import xbmc, xbmcgui

	import vsdbg
	vsdbg._bp()
	
	imdb_id = xbmc.getInfoLabel('ListItem.IMDBNumber')
	type='movie'

	from context import get_path_name
	path, name = get_path_name()

	FileNameAndPath = path.decode('utf-8')
	dbtype = xbmc.getInfoLabel('ListItem.DBTYPE')

	if dbtype == 'episode' or dbtype == 'tvshow':
		type = 'tv'

	if 'Anime' in path and not name:
		import filesystem
		if filesystem.exists('special://home/addons/plugin.video.shikimori.2'):
			import sys
			it = sys.listitem.getVideoInfoTag()
			
			try:
				import shikicore
				if shikicore.authorize_me():
					oo = shikicore.animes_search(it.getOriginalTitle())
					if oo:
						#wname = xbmc.getInfoLabel('System.CurrentWindow')
						wid = xbmcgui.getCurrentWindowId()

						uri = 'plugin://plugin.video.shikimori.2/?action=similar&id={0}'.format(oo[0]['id'])
						if wid == 10025:
							xbmc.executebuiltin(b'Container.Update(\"%s\")' % uri)
						else:
							xbmc.executebuiltin('ActivateWindow(10025,"%s")' % uri)
			except ImportError:
				pass

	if not imdb_id and dbtype == 'episode':
		from nforeader import NFOReader
		nfo_path = FileNameAndPath.replace('.strm', '.nfo')
		debug(nfo_path)
		rd = NFOReader(nfo_path, '')
		tvs_rd = rd.tvs_reader()
		imdb_id = tvs_rd.imdb_id()
		type='tv'

	if imdb_id:
		from movieapi import TMDB_API
		res = TMDB_API.tmdb_by_imdb(imdb_id, type)
		debug(res)
		if res and len(res) > 0:
			tmdb_id = res[0].tmdb_id()
			xbmc.executebuiltin('Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % tmdb_id)
			return True

	return False

if __name__ == '__main__':
	show_similar()