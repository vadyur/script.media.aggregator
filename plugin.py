import urllib, sys

import log
def make_url(params):
	url = 'plugin://script.media.aggregator/?' + urllib.urlencode(params)
	return url

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

def ScanMonitor():
	import xbmc
	class _ScanMonitor(xbmc.Monitor):
		def __init__(self):
			log.debug('ScanMonitor - __init__')
			xbmc.Monitor.__init__(self)
			self.do_exit = False
			self.do_start = xbmc.getCondVisibility('Library.IsScanningVideo')

		def onScanStarted(self, library):
			log.debug('ScanMonitor - onScanFinished')
			if library == 'video':
				self.do_start = True

		def onScanFinished(self, library):
			log.debug('ScanMonitor - onScanFinished')
			if library == 'video':
				self.do_exit = True

	return _ScanMonitor()


def wait_for_update(timeout=1000, monitor=None):
	try:
		import xbmc
		log.debug('wait_for_update')

		count = timeout

		if not monitor:
			monitor = ScanMonitor()

		if not monitor.do_start:
			log.debug('wait_for_update: no scan now')
			del monitor
			return

		while not monitor.abortRequested() and count:
			for i in xrange(10):
				if monitor.waitForAbort(0.1) or monitor.do_exit:
					log.debug('wait_for_update - Stop scan detected')
					del monitor
					return
			if count % 10 == 1:
				if not xbmc.getCondVisibility('Library.IsScanningVideo'):
					log.debug('wait_for_update - Library.IsScanningVideo is False')
					break
			count -= 1
			log.debug('wait_for_update - Library Scanning Video - wait ({}s)'.format(timeout-count))
		del monitor

	except BaseException:
		log.print_tb()

		import time
		time.sleep(1)


def UpdateVideoLibrary(path=None, wait=False):
	import xbmc, log
	if path:
		if isinstance(path,unicode):
			path = path.encode('utf-8')
		log.debug('UpdateLibrary: {}'.format(path))
		command = 'UpdateLibrary(video, {})'.format(path)
	else:
		command = 'UpdateLibrary(video)'

	if wait:
		monitor = ScanMonitor()
		while not monitor.abortRequested():
			if not monitor.do_start or monitor.do_exit:
				break
			xbmc.sleep(100)
		monitor.do_start = False

	xbmc.executebuiltin(command, wait)

	if wait:
		log.debug('UpdateLibrary: wait for start')
		while not monitor.abortRequested():
			if monitor.do_start:
				break
			xbmc.sleep(100)

		wait_for_update(monitor=monitor)

def string_to_ver(s):
	import re

	m = re.search(r'(\d+)\.(\d+)', s)
	if m:
		return ( m.group(1), m.group(2) )

def kodi_ver():
	import xbmc
	bv = xbmc.getInfoLabel("System.BuildVersion")
	BuildVersions = string_to_ver(bv)

	# import log
	# log.debug(BuildVersions)

	res = {}
	res['major'] = int(BuildVersions[0])
	res['minor'] = int(BuildVersions[1])
	return res

	

def RunPlugin(**kwargs):
	import xbmc
	url = make_url(kwargs)
	xbmc.executebuiltin('RunPlugin("%s")' % url)

def RunPluginSync(**kwargs):
	import xbmc
	url = make_url(kwargs)
	xbmc.executebuiltin('RunPlugin("%s")' % url, wait=True)


if __name__ == "__main__":
	r = string_to_ver('18.0 Git:20190128-d81c34c465')