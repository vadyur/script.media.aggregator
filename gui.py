# coding: utf-8

#from simplepluginex import debug_exception
from simplepluginex import PluginEx as Plugin

import filesystem
import xbmc, xbmcgui

from player import load_settings
#import vsdbg; vsdbg._bp()

plugin = Plugin()

def _debug(s):
	import log
	log.debug('MAGUI: ' + str(s))

def action_debug(func):
	def inner_func(params):
		from log import print_tb, debug
		try:
			return func(params)
		except:
			debug('!!! EXCEPTION Achtung !!!')
			print_tb()
		
	inner_func.__name__ = func.__name__
	return inner_func


def TMDB_API_search(s):
	from movieapi import TMDB_API
	return TMDB_API.search(s.decode('utf-8'))

@plugin.cached(30)
def TMDB_API_genres_list():
	from movieapi import TMDB_API
	return TMDB_API.genres_list()

def TMDB_API_popular_by_genre(genre, page):
	from movieapi import TMDB_API
	return TMDB_API.popular_by_genre(genre, page)
	
def add_next_item(listing, list_items, params):
	total_pages = listing.total_pages

	params = params.copy()
	if params:
		page = int(params.get('page', 1))
		if page < total_pages:
			params['page'] = page + 1
			params['url'] = plugin.get_url(**params)
			params['label'] = u'[Далее]'
			list_items.append(params)
		return page > 1
	return False
	
def get_tmdb_list_item(item):
	info = item.get_info()
	
	url_search = plugin.get_url(action='add_media', title=info['title'], imdb=item.imdb())
	url_similar = plugin.get_url(action='show_similar', type=item.type, tmdb=item.tmdb_id())
	
	art = item.get_art()
	
	return {
		'label': info['title'],
		'is_folder': False,
		'is_playable': True,
		'thumb': art['poster'],
		'fanart': art['fanart'],
		'info':  {'video': info},
		'art': art,
		'context_menu': [(u'Смотрите также', 'Container.Update("%s")' % url_similar),
						(u'Искать источники', 'RunPlugin("%s")' % (url_search + '&force=true') )],
		'url': url_search
	}
	
def show_tmdb_list(listing, params):
	# import vsdbg; vsdbg._bp()

	list_items = [ get_tmdb_list_item(item) for item in listing ]
	updateListing = add_next_item(listing, list_items, params)
	
	return Plugin.create_listing(list_items, update_listing=updateListing, cache_to_disk=True, content='movies')
	

class dialog_action_case:
	generate = 0
	sources = 1
	settings = 2
	search = 3
	catalog = 4
	medialibrary = 5
	exit = 6

@plugin.action()
def root(params):
	menu_items = (
		('generate', 	u'Генерировать .strm и .nfo файлы'),
		('sources', 	u'Создать источники'),
		('settings', 	u'Настройки'),
		('search', 		u'Поиск'),
		('catalog', 	u'Каталог'),
		('medialibrary', u'Медиатека')
	)

	indx = 0
	addon_handle = int(sys.argv[1])
	for menu, title in menu_items:
		yield { 'label': title,
				'url': plugin.get_url(action='menu_' + menu),
				'is_folder': indx > dialog_action_case.settings
				}
		
		indx += 1
		
restart_msg = u'Чтобы изменения вступили в силу, нужно перезапустить KODI. Перезапустить?'
def check_sources(settings):
	import sources
	if sources.need_create(settings):
		dialog = xbmcgui.Dialog()
		if dialog.yesno(settings.addon_name, u'Источники категорий не созданы. Создать?'):
			if sources.create(settings):
				if dialog.yesno(settings.addon_name, restart_msg):
					xbmc.executebuiltin('Quit')
			return True
		else:
			return False

	return True


@plugin.action()
def menu_generate(params):
	if not (plugin.anidub_enable or plugin.hdclub_enable or plugin.bluebird_enable or plugin.nnmclub_enable or plugin.rutor_enable or plugin.soap4me_enable or plugin.kinohd_enable):
		xbmcgui.Dialog().ok(_ADDON_NAME, u'Пожалуйста, заполните настройки', u'Ни одного сайта не выбрано')
		plugin.addon.openSettings()
	else:
		from service import start_generate
		start_generate()
		return True

@plugin.action()
def menu_sources(params):
	import sources
	settings = load_settings()

	dialog = xbmcgui.Dialog()
	if sources.create(settings):
		if dialog.yesno(settings.addon_name, restart_msg):
			from service import update_library_next_start

			update_library_next_start()
			xbmc.executebuiltin('Quit')


@plugin.action()
def menu_settings(params):
	plugin.addon.openSettings()

@plugin.action()
@action_debug
def menu_search(params):
	s = None
	if not 'keyword' in params:
		dlg = xbmcgui.Dialog()
		s = dlg.input(u'Введите поисковую строку')
		command = plugin.get_url(keyword=s, **params)
		_debug('Run command: {0}'.format(command))
		xbmc.executebuiltin('Container.Update("{0}")'.format(command))

		from plugin import kodi_ver

		if kodi_ver()['major'] < 18:
			_debug('No keyword param. Return')
			return False
	else:
		s = params.get('keyword')

	if s:
		_debug('Keyword is: ' + s)
		return show_tmdb_list(TMDB_API_search(s), params)

	
@plugin.action()
def menu_catalog(params):
	listing = [
		('popular', u'Популярные'),
		('top_rated', u'Рейтинговые'),
		('popular_tv', u'Популярные сериалы'),
		('top_rated_tv', u'Рейтинговые сериалы'),
	]

	if filesystem.exists('special://home/addons/plugin.video.shikimori.2'):
		listing.append(('anime', u'Аниме (Shikimori.org)' ), )

	for l in listing:
		yield {
			'label': l[1],
			'is_folder': True,
			'is_playable': False,
			'url': plugin.get_url(action='show_category', category=l[0])
		}

	yield {
		'label': u'Жанры',
		'is_folder': True,
		'is_playable': False,
		'url': plugin.get_url(action='genres', category=l[0])
	}

@plugin.action()
def genres(params):
	# import vsdbg; vsdbg._bp()
	for genre in TMDB_API_genres_list():
		yield {
			'label': genre['ru_name'],
			'is_folder': True,
			'is_playable': False,
			'url': plugin.get_url(action='genre_top', **genre)
		}

@plugin.action()
def genre_top(params):
	page = params.get('page', 1)
	genre = params['id']
	return show_tmdb_list(TMDB_API_popular_by_genre(genre, page), params)

@plugin.action()
def show_category(params):
	page = params.get('page', 1)

	from movieapi import TMDB_API
	if params.get('category') == 'popular':
		return show_tmdb_list(TMDB_API.popular(page), params)
	if params.get('category') == 'top_rated':
		return show_tmdb_list(TMDB_API.top_rated(page), params)
	if params.get('category') == 'popular_tv':
		return show_tmdb_list(TMDB_API.popular_tv(page), params)
	if params.get('category') == 'top_rated_tv':
		return show_tmdb_list(TMDB_API.top_rated_tv(page), params)
	if params.get('category') == 'anime':
		uri = 'plugin://plugin.video.shikimori.2/'
		xbmc.executebuiltin(b'Container.Update(\"%s\")' % uri)

	
@plugin.action()
def menu_medialibrary(params):
	listing = [

		('anime_top', u'Аниме: популярное'),
		('anime_recomended', u'Аниме: текущее'),
		('anime_last', u'Аниме: последнее'),

		('animation_top', u'Мультфильмы: популярное'),
		('animation_recomended', u'Мультфильмы: текущее'),
		('animation_last', u'Мультфильмы: последнее'),

		('animtv_top', u'Мультсериалы: популярное'),
		('animtv_recomended', u'Мультсериалы: текущее'),
		('animtv_last', u'Мультсериалы: последнее'),

		('documentary_top', u'Документальные фильмы: популярное'),
		('documentary_recomended', u'Документальные фильмы: текущее'),
		('documentary_last', u'Документальные фильмы: последнее'),

		('movie_top', u'Художественные фильмы: популярное'),
		('movie_recomended', u'Художественные фильмы: текущее'),
		('movie_last', u'Художественные фильмы: последнее'),

		('tvshow_top', u'Сериалы: популярное'),
		('tvshow_recomended', u'Сериалы: текущее'),
		('tvshow_last', u'Сериалы: последнее'),

	]

	for l in listing:
		yield {
			'label': l[1],
			'is_folder': True,
			'is_playable': False,
			'url': plugin.get_url(action='show_library', category=l[0])
		}

@plugin.action()
def show_library(params):
	from player import action_show_library
	action_show_library(params)
		
@plugin.action()
def scrape_nnm(params):
	from backgrounds import scrape_nnm
	scrape_nnm()
	
@plugin.action()
def clean_movies(params):
	from backgrounds import clean_movies
	clean_movies()

@plugin.action()
def select_source(params):
	from context import main
	main()
	
@plugin.action()
def update_service(params):
	from backgrounds import update_service
	update_service(show_progress=params.get('show_progress'))

@plugin.action()
def add_media_process(params):
	from backgrounds import add_media_process
	title = params.get('title')
	# import urllib
	# title = urllib.unquote_plus(title)
	# title = title.decode('utf-8')

	add_media_process(title, params.get('imdb'))
	
@plugin.action('anidub-add-favorites')
def anidub_add_favorites(params):
	from player import action_anidub_add_favorites
	action_anidub_add_favorites(load_settings())

@plugin.action()
def	search_context(params):
	from player import action_search_context
	action_search_context(params)

		
@plugin.action()
def play(params):
	from player import action_play
	action_play(params)

@plugin.action()
def show_similar(params):
	from player import action_show_similar
	action_show_similar(params)

@plugin.action()
def add_media(params):
	from player import action_add_media
	action_add_media(params, load_settings())


if __name__ == '__main__':
	plugin.run()  # Start plugin