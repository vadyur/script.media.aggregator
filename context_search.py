import urllib2, xbmc

def main():
	Label = xbmc.getInfoLabel("ListItem.Label")
	#xbmc.executebuiltin("XBMC.ActivateWindow(Video, plugin://script.media.aggregator/?action=search_context&s=%s, return)" % (urllib2.quote(Label)))
	command = 'plugin://script.media.aggregator/?action=search&keyword=' + urllib2.quote(Label)
	xbmc.executebuiltin(b'Container.Update(\"%s\")' % command)

if __name__ == '__main__':
	#import brkpnt
	#brkpnt._bp()

	main()