import urllib2, xbmc

def main():
	Label = xbmc.getInfoLabel("ListItem.Label")
	xbmc.executebuiltin("XBMC.ActivateWindow(Video, plugin://script.media.aggregator/?action=search_context&s=%s, return)" % (urllib2.quote(Label)))

if __name__ == '__main__':
	main()