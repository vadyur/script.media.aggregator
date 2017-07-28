from log import debug

def show_similar():
	import xbmc

	import vsdbg
	vsdbg._bp()
	
	imdb_id = xbmc.getInfoLabel('ListItem.IMDBNumber')
	type='movie'

	from context import get_path_name
	path, name = get_path_name()

	FileNameAndPath = path.decode('utf-8')
	dbtype = xbmc.getInfoLabel('ListItem.DBTYPE')

	if 'Anime' in path and not name:
		import filesystem
		if filesystem.exists('special://home/addons/plugin.video.shikimori.2'):
			import sys
			it = sys.listitem.getVideoInfoTag()

			import shikicore
			oo = shikicore.animes_search(it.getOriginalTitle())
			if oo:
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
		from movieapi import MovieAPI
		res = MovieAPI.tmdb_by_imdb(imdb_id, type)
		debug(res)
		if res and len(res) > 0:
			tmdb_id = res[0].tmdb_id()
			xbmc.executebuiltin('Container.Update("plugin://script.media.aggregator/?action=show_similar&tmdb=%s")' % tmdb_id)
			return True

	return False

if __name__ == '__main__':
	show_similar()