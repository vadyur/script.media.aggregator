from log import *
import xbmc

def main():
	
	imdb_id = xbmc.getInfoLabel('ListItem.IMDBNumber')
	title = xbmc.getInfoLabel('ListItem.Title')

	debug(imdb_id)
	debug(title)

	from service import add_media
	add_media(title.decode('utf-8'), imdb_id)

	
main()