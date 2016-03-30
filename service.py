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
import player

import xml.etree.ElementTree as ET

_ADDON_NAME =   'script.media.aggregator'
_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)
_addondir   = xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')

class AddonRO(object):
	def __init__(self, xml_filename='settings.xml'):
		self._addon_xml 	= filesystem.join(_addondir, xml_filename)
		self.check_exists()
		self.load()

	def check_exists(self):
		pass

	def load(self):
		if not filesystem.exists(self._addon_xml):
			self.root = None
			self.mtime = 0
			return

		with filesystem.fopen(self._addon_xml, 'r') as f:
			content = f.read()
			self.root = ET.fromstring(content)
		self.mtime = filesystem.getmtime(self._addon_xml)


	# get setting no caching
	def getSetting(self, s):
		if not filesystem.exists(self._addon_xml):
			return u''

		if self.mtime != filesystem.getmtime(self._addon_xml):
			self.load()

		for item in self.root:
			if item.get('id') == s:
				return item.get('value').encode('utf-8')
		return u''

class Addon(AddonRO):

	@staticmethod
	def _xml(data):
		return data.replace("&", "&amp;").replace("<", "&lt;").replace("\"", "&quot;").replace(">", "&gt;")

	def check_exists(self):
		if not filesystem.exists(self._addon_xml):
			with filesystem.fopen(self._addon_xml, 'w') as f:
				f.write('<settings>\n')
				f.write('</settings>\n')

	def setSetting(self, id, val):
		item = self.root.find("./setting[@id='%s']" % str(id))
		if item is not None:
			item.set('value', str(val))
		else:
			ET.SubElement(self.root, 'setting', attrib={'id': str(id), 'value': str(val)})

		with filesystem.fopen(self._addon_xml, 'w') as f:
			f.write('<settings>\n')
			for item in self.root:
				f.write('    <setting id="%s" value="%s" />\n' % (Addon._xml(item.get('id')), Addon._xml(item.get('value'))))
			f.write('</settings>\n')

		self.mtime = filesystem.getmtime(self._addon_xml)


def update_service(show_progress=False):

	anidub_enable		= _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable		= _addon.getSetting('hdclub_enable') == 'true'
	nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'
	settings			= player.load_settings()

	if show_progress:
		info_dialog = xbmcgui.DialogProgressBG()
		info_dialog.create('Media Aggregator')
		settings.progress_dialog = info_dialog
	
	if anidub_enable:
		anidub.run(settings)

	if hdclub_enable:
		hdclub.run(settings)

	if nnmclub_enable:
		addon = Addon('settings2.xml')

		try:
			settings.nnmclub_hours = int(math.ceil((time() - float(addon.getSetting('nnm_last_generate'))) / 3600.0))
		except BaseException as e:
			settings.nnmclub_hours = 168
			log.debug(e)

		if settings.nnmclub_hours > 168:
			settings.nnmclub_hours = 168

		log.debug('NNM hours: ' + str(settings.nnmclub_hours))

		addon.setSetting('nnm_last_generate', str(time()))
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
	data_path = _addondir

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
		except RuntimeError as RunE:
			if '414 status code returned' in RunE.message:
				for c in chunks(chunk, 16):
					try:
						seeds_peers = scraper.scrape(c[0][0], [i[1] for i in c])
						process_chunk(c, data_path, seeds_peers)
					except BaseException as e:
						log.debug(e)
			continue
		except BaseException as e:
			log.debug(e)
			continue

		process_chunk(chunk, data_path, seeds_peers)


def process_chunk(chunk, data_path, seeds_peers):
	import json

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

	try:
		every = int(_addon.getSetting('service_generate_persistent_every')) * 3600 # seconds
		delay_startup = int(_addon.getSetting('delay_startup')) * 60
	except ValueError:
		every = 8 * 3600
		delay_startup = 0

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
		if _addon.getSetting('service_startup') == 'true':
			try:
				log.debug("Persistent Update Service starting...")
				log.debug(_addon.getSetting('service_startup'))
				update_service(show_progress=False)
			except BaseException as e:
				log.debug(e)
			finally:
				update_case.first_start = False

	# Persistent
	if time() >= update_case.prev_generate_time + every:  # verification
		if _addon.getSetting('service_generate_persistent') == 'true':
			try:
				update_case.prev_generate_time = time()
				update_service(show_progress=False)
				log.debug('Update List at %s' % asctime(localtime(update_case.prev_generate_time)))
				log.debug('Next Update in %s' % strftime("%H:%M:%S", gmtime(every)))
			except BaseException as e:
				log.debug(e)
			finally:
				update_case.first_start = False


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
	global _addon
	_addon = AddonRO()
	player._addon = _addon

	path = filesystem.join(_addondir, 'update_library_next_start')
	if filesystem.exists(path):
		log.debug('User action!!! update_library_next_start')
		xbmc.executebuiltin('UpdateLibrary("video")')
		filesystem.remove(path)


	while not xbmc.abortRequested:

		try:
			scrape_case()
			update_case()

		finally:
			sleep(1)

	log.debug('service exit')


def start_generate():
	path = filesystem.join(_addondir, 'start_generate')
	if not filesystem.exists(path):
		with filesystem.fopen(path, 'w'):
			pass

def update_library_next_start():
	path = filesystem.join(_addondir, 'update_library_next_start')
	if not filesystem.exists(path):
		with filesystem.fopen(path, 'w'):
			pass


if __name__ == '__main__':
	main()