import urllib.request, urllib.error, urllib.parse, xbmc, re

def main():
	Label = xbmc.getInfoLabel("ListItem.Label")
	Label = re.sub('\[.+\]', '', Label).strip()

	#xbmc.executebuiltin("XBMC.ActivateWindow(Video, plugin://script.media.aggregator/?action=search_context&s=%s, return)" % (urllib2.quote(Label)))
	command = 'plugin://script.media.aggregator/?action=search&keyword=' + urllib.parse.quote(Label)
	xbmc.executebuiltin(b'Container.Update(\"%s\")' % command)

if __name__ == '__main__':
	main()