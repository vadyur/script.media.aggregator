import sys

from plugin import get_params

def dispatch():
	from log import debug

	params = get_params()
	debug(params)

	from player import load_settings

	#import vsdbg
	#vsdbg._bp()
	
	if 'torrent' in params:
		from player import play_torrent

		settings = load_settings()

		skip_show_sources = False

		if settings.show_sources and 'onlythis' not in params:
			import filesystem, urllib

			rel_path = urllib.unquote(params['path']).decode('utf-8')
			debug(rel_path)

			filename = urllib.unquote(params['nfo']).decode('utf-8').replace(u'.nfo', u'.strm')
			debug(filename)

			path = filesystem.join(settings.base_path(), rel_path, filename)
			path = filesystem.normseps(path)
			debug(path)

			def run(run_params):
				play_torrent(settings=settings, params=run_params)

			if settings.skip_show_sources:
				from base import STRMWriterBase
				links_with_ranks = STRMWriterBase.get_links_with_ranks(path, settings)

				from base import is_torrent_remembed
				for v in links_with_ranks:
					if is_torrent_remembed(v, settings):
						play_torrent(settings=settings, params=params)
						return

			import context
			res = context.main(settings, path.encode('utf-8'), filename.encode('utf-8'), run)
			if not res:
				play_torrent(settings=settings, params=params)
		else:
			play_torrent(settings=settings, params=params)
	
	elif params.get('action') == 'anidub-add-favorites':
		from player import action_anidub_add_favorites
		action_anidub_add_favorites(load_settings())
	
	elif params.get('action') == 'settings':
		from player import dialog_action, dialog_action_case
		dialog_action(dialog_action_case.settings, load_settings())
	
	elif params.get('action') == 'search':
		from player import dialog_action, dialog_action_case
		dialog_action(dialog_action_case.search, load_settings(), params)
	
	elif params.get('action') == 'search_context':
		from player import action_search_context
		action_search_context(params)
	
	elif params.get('action') == 'catalog':
		from player import dialog_action, dialog_action_case
		dialog_action(dialog_action_case.catalog, load_settings())
	
	elif params.get('action') == 'show_category':
		from player import action_show_category
		action_show_category(params)

	elif params.get('action') == 'show_library':
		from player import action_show_library
		action_show_library(params)
	
	elif params.get('action') == 'show_similar':
		from player import action_show_similar
		action_show_similar(params)
	
	elif params.get('action') == 'add_media':
		#vsdbg._bp()

		from player import action_add_media
		action_add_media(params, load_settings())

	elif params.get('action') == 'update_service':
		#vsdbg._bp()
		from backgrounds import update_service
		update_service(show_progress=params.get('show_progress'))

	elif params.get('action') == 'scrape_nnm':
		from backgrounds import scrape_nnm
		scrape_nnm()

	elif params.get('action') == 'clean_movies':
		from backgrounds import clean_movies
		clean_movies()

	elif params.get('action') == 'select_source':
		from context import main
		#vsdbg._bp()
		main()

	elif params.get('action') == 'add_media_process':
		#vsdbg._bp()

		from backgrounds import add_media_process
		title = params.get('title')
		import urllib
		title = urllib.unquote_plus(title)
		title = title.decode('utf-8')
	
		add_media_process(title, params.get('imdb'))
	
	else:
		from player import menu_actions, dialog_action, main_menu
		if params.get('menu') in menu_actions:
			dialog_action(menu_actions.index(params.get('menu')), load_settings(), params)
		else:
			main_menu(menu_actions)
