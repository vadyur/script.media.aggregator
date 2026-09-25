import urllib.parse, xbmc, re

def main() -> None:
	Label = xbmc.getInfoLabel("ListItem.Label")
	Label = re.sub(r'\[.+\]', '', Label).strip()

	#xbmc.executebuiltin("XBMC.ActivateWindow(Video, plugin://script.media.aggregator/?action=search_context&s=%s, return)" % (urllib2.quote(Label)))
	command = 'plugin://script.media.aggregator/?action=search&keyword=' + urllib.parse.quote(Label)
	xbmc.executebuiltin('Container.Update("%s")' % command)

if __name__ == '__main__':
	main()