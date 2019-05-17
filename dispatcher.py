import sys

from plugin import get_params

def dispatch():
	from log import debug

	params = get_params()
	debug(params)

	from player import load_settings

	import vsdbg
	vsdbg._bp()
	
	if False:
		pass
	
	# elif params.get('action') == 'update_service':
	# 	vsdbg._bp()
	# 	from backgrounds import update_service
	# 	update_service(show_progress=params.get('show_progress'))

	# elif params.get('action') == 'scrape_nnm':
	# 	from backgrounds import scrape_nnm
	# 	scrape_nnm()

	# elif params.get('action') == 'clean_movies':
	# 	from backgrounds import clean_movies
	# 	clean_movies()

	# elif params.get('action') == 'select_source':
	# 	from context import main
	# 	vsdbg._bp()
	# 	main()

	# elif params.get('action') == 'add_media_process':
	# 	#vsdbg._bp()
    # 
	# 	from backgrounds import add_media_process
	# 	title = params.get('title')
	# 	import urllib
	# 	title = urllib.unquote_plus(title)
	# 	title = title.decode('utf-8')
	# 
	# 	add_media_process(title, params.get('imdb'))
	
	else:
		from player import menu_actions, dialog_action, main_menu
		if params.get('menu') in menu_actions:
			dialog_action(menu_actions.index(params.get('menu')), load_settings(), params)
		else:
			main_menu(menu_actions)
