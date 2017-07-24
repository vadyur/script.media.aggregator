import sys

def get_params():
	if len(sys.argv) < 3:
		return None

	param = dict()

	paramstring = sys.argv[2]
	if len(paramstring) >= 2:
		params = sys.argv[2]
		cleanedparams = params.replace('?', '')
		if (params[len(params) - 1] == '/'):
			params = params[0:len(params) - 2]
		pairsofparams = cleanedparams.split('&')
		param = {}
		for i in range(len(pairsofparams)):
			splitparams = {}
			splitparams = pairsofparams[i].split('=')
			if (len(splitparams)) == 2:
				param[splitparams[0]] = splitparams[1]

	# debug(param)
	return param

def dispatch():
	from log import debug

	params = get_params()
	debug(params)

	from player import load_settings

	import vsdbg
	vsdbg._bp()
	
	if 'torrent' in params:
		from player import play_torrent
		play_torrent(settings=load_settings(), params=params)
	
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
	
	elif params.get('action') == 'show_similar':
		from player import action_show_similar
		action_show_similar(params)
	
	elif params.get('action') == 'add_media':
		from player import action_add_media
		action_add_media(params, load_settings())

	elif params.get('action') == 'update_service':
		from backgrounds import update_service
		update_service(show_progress=params.get('show_progress'))

	elif params.get('action') == 'scrape_nnm':
		from backgrounds import scrape_nnm
		scrape_nnm()

	elif params.get('action') == 'add_media_process':
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
