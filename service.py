# coding: utf-8

import xbmc, xbmcaddon

from time import time
from time import asctime
from time import localtime
from time import strftime
from time import gmtime
from time import sleep

import anidub, hdclub, nnmclub
from player import load_settings

_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)

def update_service():
	anidub_enable		= _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable		= _addon.getSetting('hdclub_enable') == 'true'
	nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'
	settings			= load_settings()
	
	if anidub_enable:
		anidub.run(settings)
	if hdclub_enable:
		hdclub.run(settings)
	if nnmclub_enable:
		nnmclub.run(settings)
	
	if anidub_enable or hdclub_enable or nnmclub_enable:
		xbmc.executebuiltin('UpdateLibrary("video")')

def main():
	previous_time = time()
	every = int(_addon.getSetting('service_generate_persistent_every')) * 3600 # seconds

	delay_startup = int(_addon.getSetting('delay_startup')) * 60

	if _addon.getSetting('service_startup') == 'true':
		
		for i in range(delay_startup):
			if xbmc.abortRequested:
				return
			sleep(1)
			
		xbmc.log("Persistent Update Service starting...")
		print _addon.getSetting('service_startup')
		update_service()
		
	while (not xbmc.abortRequested) and _addon.getSetting('service_generate_persistent') == 'true':
		if time() >= previous_time + every:  # verification
			previous_time = time()
			update_service()
			xbmc.log('Update List at %s' % asctime(localtime(previous_time)))
			xbmc.log('Next Update in %s' % strftime("%H:%M:%S", gmtime(every)))
		sleep(1)

if __name__ == '__main__':
	main()