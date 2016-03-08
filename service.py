# coding: utf-8
import log

import xbmc, xbmcaddon

from time import time
from time import asctime
from time import localtime
from time import strftime
from time import gmtime
from time import sleep

import anidub, hdclub, nnmclub
import filesystem
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
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video")')

def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in xrange(0, len(l), n):
		yield l[i:i+n]

def scrape_nnm(settings = None):
	import json

	if settings is None:
		settings = load_settings()
	data_path = settings.addon_data_path

	hashes = []
	for torr in filesystem.listdir(filesystem.join(data_path, 'nnmclub')):
		if torr.endswith('.torrent'):
			from base import TorrentPlayer
			tp = TorrentPlayer()
			tp.AddTorrent(filesystem.join(data_path, 'nnmclub', torr))
			data = tp.GetLastTorrentData()
			if data:
				hashes.append((data['announce'], data['info_hash'], torr.replace('.torrent', '.stat')))

	for chunk in chunks(hashes, 32):
		import scraper
		try:
			seeds_peers = scraper.scrape(chunk[0][0], [i[1] for i in chunk])
		except BaseException as e:
			log.debug(str(e))
			continue

		for item in chunk:
			filename = filesystem.join(data_path, 'nnmclub', item[2])
			remove_file = False
			with filesystem.fopen(filename, 'w') as stat_file:
				try:
					json.dump(seeds_peers[item[1]], stat_file)
				except KeyError as e:
					remove_file = True
					log.debug(e)
			if remove_file:
				filesystem.remove(filename)

def main():
	previous_time = time()
	prev_scrape_time = time()

	every = int(_addon.getSetting('service_generate_persistent_every')) * 3600 # seconds
	scrape_every = 30 * 60

	delay_startup = int(_addon.getSetting('delay_startup')) * 60

	scrape_nnm()
	log.debug('scrape_nnm')

	if _addon.getSetting('service_startup') == 'true':
		
		for i in range(delay_startup):
			if xbmc.abortRequested:
				return
			sleep(1)
			
		log.debug("Persistent Update Service starting...")
		log.debug(_addon.getSetting('service_startup'))
		update_service()
		
	while (not xbmc.abortRequested):
		if time() >= prev_scrape_time + scrape_every:
			prev_scrape_time = time()
			scrape_nnm()
			log.debug('scrape_nnm')

		if _addon.getSetting('service_generate_persistent') == 'true':
			if time() >= previous_time + every:  # verification
				previous_time = time()
				update_service()
				log.debug('Update List at %s' % asctime(localtime(previous_time)))
				log.debug('Next Update in %s' % strftime("%H:%M:%S", gmtime(every)))

		sleep(1)

if __name__ == '__main__':
	main()