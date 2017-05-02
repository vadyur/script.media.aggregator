import urllib, xbmc
title = xbmc.getInfoLabel('ListItem.Title')

if xbmc.getInfoLabel('ListItem.DBTYPE') == 'episode':
	title = xbmc.getInfoLabel('ListItem.TVShowTitle')
xbmc.executebuiltin('Container.Update("plugin://plugin.video.united.search/?action=search&keyword=%s")' % urllib.quote(title))
