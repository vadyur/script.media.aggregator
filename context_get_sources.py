from log import debug
import xbmc


def get_sources(settings):
	imdb_id = xbmc.getInfoLabel('ListItem.IMDBNumber')
	title = xbmc.getInfoLabel('ListItem.Title')

	debug(imdb_id)
	debug(title)

	from service import add_media
	add_media(title.decode('utf-8'), imdb_id, settings)

if __name__ == '__main__':
	from player import load_settings
	
	settings = load_settings()
	get_sources(settings)