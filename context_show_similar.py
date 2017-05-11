from log import debug
import xbmc

def show_similar():
	imdb_id = xbmc.getInfoLabel('ListItem.IMDBNumber')
	type='movie'

	if not imdb_id and xbmc.getInfoLabel('ListItem.DBTYPE') == 'episode':
		from nforeader import NFOReader
		nfo_path = xbmc.getInfoLabel('ListItem.FileNameAndPath').replace('.strm', '.nfo').decode('utf-8')
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