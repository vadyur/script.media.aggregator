# coding: utf-8
import math

import log

import xbmc, xbmcaddon, xbmcgui

from time import time
from time import asctime
from time import localtime
from time import strftime
from time import gmtime
from time import sleep

import anidub, hdclub, nnmclub
import filesystem
from player import load_settings

import xml.etree.ElementTree as ET

_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)
_addondir   = xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')
_addon_xml 	= filesystem.join(_addondir, 'settings.xml')


class Addon(object):
	def __init__(self, xmlPath):
		with filesystem.fopen(xmlPath, 'r') as f:
			content = f.read()
			self.root = ET.fromstring(content)

	# get setting no caching
	def getSetting(self, s):
		for item in self.root:
			if item.get('id') == s:
				return item.get('value').encode('utf-8')
		return u''


def update_service(show_progress=False):
	addon = Addon(_addon_xml)

	anidub_enable		= addon.getSetting('anidub_enable') == 'true'
	hdclub_enable		= addon.getSetting('hdclub_enable') == 'true'
	nnmclub_enable		= addon.getSetting('nnmclub_enable') == 'true'
	settings			= load_settings()

	if show_progress:
		info_dialog = xbmcgui.DialogProgressBG()
		info_dialog.create('Media Aggregator')
		settings.progress_dialog = info_dialog
	
	if anidub_enable:
		anidub.run(settings)

	if hdclub_enable:
		hdclub.run(settings)

	if nnmclub_enable:
		try:
			settings.nnmclub_hours = int(math.ceil((time() - float(_addon.getSetting('nnm_last_generate'))) / 3600.0))
		except BaseException as e:
			settings.nnmclub_hours = 168
			log.debug(e)

		if settings.nnmclub_hours > 168:
			settings.nnmclub_hours = 168

		log.debug('NNM hours: ' + str(settings.nnmclub_hours))

		_addon.setSetting('nnm_last_generate', str(time()))
		nnmclub.run(settings)

	if show_progress:
		info_dialog.update(0, '', '')
		info_dialog.close()

	if anidub_enable or hdclub_enable or nnmclub_enable:
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video")')


def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in xrange(0, len(l), n):
		yield l[i:i+n]


def scrape_nnm():
	import json

	data_path = _addondir #settings.addon_data_path

	hashes = []
	for torr in filesystem.listdir(filesystem.join(data_path, 'nnmclub')):
		if torr.endswith('.torrent'):
			try:
				from base import TorrentPlayer
				tp = TorrentPlayer()
				tp.AddTorrent(filesystem.join(data_path, 'nnmclub', torr))
				data = tp.GetLastTorrentData()
				if data:
					hashes.append((data['announce'], data['info_hash'], torr.replace('.torrent', '.stat')))
			except BaseException as e:
				log.debug(e)

	for chunk in chunks(hashes, 32):
		import scraper
		try:
			seeds_peers = scraper.scrape(chunk[0][0], [i[1] for i in chunk])
		except BaseException as e:
			log.debug(e)
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


def update_case():
	# Init
	if not hasattr(update_case, 'first_start'):
		update_case.first_start = True
		update_case.first_start_time = time()
		update_case.prev_generate_time = update_case.first_start_time
	every = int(_addon.getSetting('service_generate_persistent_every')) * 3600 # seconds
	delay_startup = int(_addon.getSetting('delay_startup')) * 60

	# User action
	path = filesystem.join(_addondir, 'start_generate')
	if filesystem.exists(path):
		log.debug('User action!!!')

		filesystem.remove(path)
		update_service(show_progress=True)
		update_case.first_start = False
		return

	# Startup
	if time() > update_case.first_start_time + delay_startup and update_case.first_start:
		if Addon(_addon_xml).getSetting('service_startup') == 'true':
			try:
				log.debug("Persistent Update Service starting...")
				log.debug(_addon.getSetting('service_startup'))
				update_service(show_progress=False)
				update_case.first_start = False
			except BaseException as e:
				log.debug(e)

	# Persistent
	if time() >= update_case.prev_generate_time + every:  # verification
		if Addon(_addon_xml).getSetting('service_generate_persistent') == 'true':
			try:
				update_case.prev_generate_time = time()
				update_service(show_progress=False)
				update_case.first_start = False
				log.debug('Update List at %s' % asctime(localtime(update_case.prev_generate_time)))
				log.debug('Next Update in %s' % strftime("%H:%M:%S", gmtime(every)))
			except BaseException as e:
				log.debug(e)


def scrape_case():
	# Init
	if not hasattr(scrape_case, 'prev_scrape_time'):
		try:
			scrape_nnm()
			log.debug('scrape_nnm')
		except BaseException as e:
			log.debug(e)
		scrape_case.prev_scrape_time = time()

	scrape_every = 30 * 60
	if time() >= scrape_case.prev_scrape_time + scrape_every:
		try:
			scrape_case.prev_scrape_time = time()
			scrape_nnm()
			log.debug('scrape_nnm')
		except BaseException as e:
			log.debug(e)


def main():
	while not xbmc.abortRequested:

		scrape_case()
		update_case()

		sleep(1)


def start_generate():
	path = filesystem.join(_addondir, 'start_generate')
	if not filesystem.exists(path):
		with filesystem.fopen(path, 'w'):
			pass


if __name__ == '__main__':
	main()