# coding: utf-8
import math, urllib

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
_addondir   =   xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')


# ------------------------------------------------------------------------------------------------------------------- #
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


# ------------------------------------------------------------------------------------------------------------------- #
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
		# not work in Python 2.6
		# item = self.root.find("./setting[@id='%s']" % str(id))

		item = None
		settings = self.root.findall("setting")
		for setting in settings:
			if setting.attrib.get('id') == id:
				item = setting
				break

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


# ------------------------------------------------------------------------------------------------------------------- #
def addon_data_path():
	if _addon.getSetting('data_path'):
		return _addon.getSetting('data_path')
	else:
		return _addondir


# ------------------------------------------------------------------------------------------------------------------- #
def update_service(show_progress=False):

	anidub_enable		= _addon.getSetting('anidub_enable') == 'true'
	hdclub_enable		= _addon.getSetting('hdclub_enable') == 'true'
	nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'
	rutor_enable		= _addon.getSetting('rutor_enable') == 'true'
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
			log.print_tb(e)

		if settings.nnmclub_hours > 168:
			settings.nnmclub_hours = 168

		log.debug('NNM hours: ' + str(settings.nnmclub_hours))

		addon.setSetting('nnm_last_generate', str(time()))
		nnmclub.run(settings)

	if rutor_enable:
		import rutor
		rutor.run(settings)

	if show_progress:
		info_dialog.update(0, '', '')
		info_dialog.close()

	if anidub_enable or hdclub_enable or nnmclub_enable or rutor_enable:
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video")')


# ------------------------------------------------------------------------------------------------------------------- #
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in xrange(0, len(l), n):
		yield l[i:i + n]


# ------------------------------------------------------------------------------------------------------------------- #
def scrape_nnm():
	settings = player.load_settings()
	data_path = settings.torrents_path()

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
				log.print_tb(e)

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
						log.print_tb(e)
			continue
		except BaseException as e:
			log.print_tb(e)
			continue

		process_chunk(chunk, data_path, seeds_peers)


# ------------------------------------------------------------------------------------------------------------------- #
def process_chunk(chunk, data_path, seeds_peers):
	import json

	for item in chunk:
		filename = filesystem.join(data_path, 'nnmclub', item[2])
		remove_file = False
		with filesystem.fopen(filename, 'w') as stat_file:
			try:
				json.dump(seeds_peers[item[1]], stat_file)
			except KeyError:
				remove_file = True
		if remove_file:
			filesystem.remove(filename)


# ------------------------------------------------------------------------------------------------------------------- #
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
	path = filesystem.join(addon_data_path(), 'start_generate')

	if filesystem.exists(path) and _addon.getSetting('role').decode('utf-8') != u'клиент':

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
				log.print_tb(e)
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
				log.print_tb(e)
			finally:
				update_case.first_start = False


# ------------------------------------------------------------------------------------------------------------------- #
def scrape_case():
	# Init
	if not hasattr(scrape_case, 'prev_scrape_time'):
		try:
			scrape_nnm()
			log.debug('scrape_nnm at %s' % asctime())
		except BaseException as e:
			log.print_tb(e)
		scrape_case.prev_scrape_time = time()

	scrape_every = 30 * 60
	if time() >= scrape_case.prev_scrape_time + scrape_every:
		try:
			scrape_case.prev_scrape_time = time()
			scrape_nnm()
			log.debug('scrape_nnm at %s' % asctime())
		except BaseException as e:
			log.print_tb(e)


# ------------------------------------------------------------------------------------------------------------------- #
def add_media_process(title, imdb, settings):
	#import rpdb2
	#rpdb2.start_embedded_debugger('pw')
	count = 0

	hdclub_enable		= _addon.getSetting('hdclub_enable') == 'true'
	nnmclub_enable		= _addon.getSetting('nnmclub_enable') == 'true'

	if hdclub_enable:
		count += hdclub.search_generate(title, imdb, settings)
	if nnmclub_enable:
		count += nnmclub.search_generate(title, imdb, settings)

	if count:
		if not xbmc.getCondVisibility('Library.IsScanningVideo'):
			xbmc.executebuiltin('UpdateLibrary("video")')

	path = filesystem.join(addon_data_path(), imdb + '.ended')
	with filesystem.fopen(path, 'w') as f:
		f.write(str(count))


# ------------------------------------------------------------------------------------------------------------------- #
def add_media_case():
	if _addon.getSetting('role').decode('utf-8') == u'клиент':
		return

	path = filesystem.join(addon_data_path(), 'add_media')
	if filesystem.exists(path):
		with filesystem.fopen(path, 'r') as f:
			while True:
				try:
					title = f.readline().strip(' \n\t\r').decode('utf-8')
					imdb = f.readline().strip(' \n\t\r')

					log.debug('add_media_case: ' + imdb)
					log.debug(title)

					if title and imdb:
						add_media_process(title, imdb, player.load_settings())
					else:
						break
				except BaseException as e:
					log.print_tb(e)

		filesystem.remove(path)


# ------------------------------------------------------------------------------------------------------------------- #
def main():
	global _addon
	_addon = AddonRO()
	player._addon = _addon

	path = filesystem.join(addon_data_path(), 'update_library_next_start')
	if filesystem.exists(path):
		log.debug('User action!!! update_library_next_start')
		xbmc.executebuiltin('UpdateLibrary("video")')
		filesystem.remove(path)


	cnt = 0
	while not xbmc.abortRequested:

		try:
			scrape_case()
			update_case()
			add_media_case()

		finally:
			sleep(1)

		if cnt % 3600 == 0:
			log.debug("I'm alive at %s" % asctime())
		cnt += 1

	log.debug('service exit')


# ------------------------------------------------------------------------------------------------------------------- #
def start_generate():
	path = filesystem.join(addon_data_path(), 'start_generate')
	if not filesystem.exists(path):
		with filesystem.fopen(path, 'w'):
			pass


# ------------------------------------------------------------------------------------------------------------------- #
def update_library_next_start():
	path = filesystem.join(addon_data_path(), 'update_library_next_start')
	if not filesystem.exists(path):
		with filesystem.fopen(path, 'w'):
			pass


# ------------------------------------------------------------------------------------------------------------------- #
def add_media(title, imdb):
	path = filesystem.join(addon_data_path(), 'add_media')
	log.debug(path)

	# if not filesystem.exists(path):
	# 	with filesystem.fopen(path, 'w'):
	# 		pass

	if filesystem.exists(path):
		with filesystem.fopen(path, 'r') as f:
			s = f.read()
			if imdb.encode('utf-8') in s:
				return

	with filesystem.fopen(path, 'a+') as f:
		log.debug('writing...')
		seq = [title.encode('utf-8') + '\n', imdb.encode('utf-8') + '\n']
		f.writelines(seq)

	ended_path = filesystem.join(addon_data_path(), imdb + '.ended')
	for cnt in range(300):

		if filesystem.exists(ended_path):
			with filesystem.fopen(ended_path, 'r') as f:
				dlg = xbmcgui.Dialog()

				count = f.read()

				try:
					count = int(count)
				except BaseException:
					count = 0

				if count:
					dlg.notification(u'Media Aggregator', u'"%s" добавлено в библиотеку, найдено %d источников.' % (title, count), time=10000)

					url = 'plugin://script.media.aggregator/?' + urllib.urlencode(
						{'action': 'add_media',
						 'title': title.encode('utf-8'),
						 'imdb': imdb,
						 'norecursive': True})

					xbmc.executebuiltin('RunPlugin("%s")' % url)
				else:
					dlg.notification(u'Media Aggregator',
					                 u'"%s" не добавлено в библиотеку, Источники не найдены.' % title,
					                 time=10000)
			filesystem.remove(ended_path)

			break

		sleep(1)


# ------------------------------------------------------------------------------------------------------------------- #
def save_dbs():
	path = filesystem.join(_addondir, 'dbversions')

	with filesystem.save_make_chdir_context(path):

		for fn in filesystem.listdir(path):
			filesystem.remove(fn)

		log_dir = xbmc.translatePath('special://logpath').decode('utf-8')
		log_path = filesystem.join(log_dir, 'kodi.log')
		log.debug(log_path)
		with filesystem.fopen(log_path, 'r') as lf:
			for line in lf.readlines():
				if 'Running database version' in line:
					log.debug(line)
					name = line.split(' ')[-1].strip('\r\n\t ').decode('utf-8')
					with filesystem.fopen(name, 'w'):
						pass


# ------------------------------------------------------------------------------------------------------------------- #
def create_mark_file():
	import urllib2, shutil
	path = filesystem.join(_addondir, 'version_015')
	if not filesystem.exists(path):
		url = 'https://github.com/vadyur/script.media.aggregator/releases/download/ver_0.15.1/version_015'
		response = urllib2.urlopen(url)
		with filesystem.fopen(path, 'w') as f:
			shutil.copyfileobj(response, f)


# ------------------------------------------------------------------------------------------------------------------- #
if __name__ == '__main__':
	try:
		create_mark_file()
		save_dbs()
	except BaseException as e:
		log.print_tb(e)
		pass

	main()