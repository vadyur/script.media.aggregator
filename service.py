# coding: utf-8

import math, urllib
import log

try:
	import xbmc, xbmcaddon, xbmcgui
except ImportError:
	pass

from time import time
from time import asctime
from time import localtime
from time import strftime
from time import gmtime
from time import sleep

import filesystem
try:
	import player
except ImportError:
	pass

import xml.etree.ElementTree as ET

_ADDON_NAME =   'script.media.aggregator'
try:
	_addon      =   xbmcaddon.Addon(id=_ADDON_NAME)
	_addondir   =   xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')
except:
	pass

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
def call_bg(action, params = {}):
	params['action'] = action

	for key, value in params.iteritems(): 
		if isinstance(value, unicode):
			params[key] = value.encode('utf-8')
	url = 'plugin://script.media.aggregator/?' + urllib.urlencode(params)
	xbmc.executebuiltin('RunPlugin("%s")' % url)

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
		call_bg('update_service', {'show_progress': True})

		update_case.first_start = False
		return

	# Startup
	if time() > update_case.first_start_time + delay_startup and update_case.first_start:
		if _addon.getSetting('service_startup') == 'true':
			try:
				log.debug("Persistent Update Service starting...")
				log.debug(_addon.getSetting('service_startup'))
				#update_service(show_progress=False)
				call_bg('update_service', {	'show_progress': False })
			except BaseException as e:
				log.print_tb(e)
			finally:
				update_case.first_start = False

	# Persistent
	if time() >= update_case.prev_generate_time + every:  # verification
		if _addon.getSetting('service_generate_persistent') == 'true':
			try:
				update_case.prev_generate_time = time()
				#update_service(show_progress=False)
				call_bg('update_service', {'show_progress': False})
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
			#scrape_nnm()
			call_bg('scrape_nnm')
			log.debug('scrape_nnm at %s' % asctime())
		except BaseException as e:
			log.print_tb(e)
		scrape_case.prev_scrape_time = time()

	scrape_every = 30 * 60
	if time() >= scrape_case.prev_scrape_time + scrape_every:
		try:
			scrape_case.prev_scrape_time = time()
			#scrape_nnm()
			call_bg('scrape_nnm')

			log.debug('scrape_nnm at %s' % asctime())
		except BaseException as e:
			log.print_tb(e)



# ------------------------------------------------------------------------------------------------------------------- #
def add_media_case():
	if _addon.getSetting('role').decode('utf-8') == u'клиент':
		return

	path = filesystem.join(addon_data_path(), 'add_media')
	if filesystem.exists(path):
		try:
			with filesystem.fopen(path, 'r') as f:
				while True:
					try:
						title = f.readline().strip(' \n\t\r').decode('utf-8')
						imdb = f.readline().strip(' \n\t\r')

						log.debug('add_media_case: ' + imdb)
						log.debug(title)

						if title and imdb:
							call_bg( 'add_media_process', {'title': title, 'imdb': imdb} )
						else:
							break
					except BaseException as e:
						log.print_tb(e)
		finally:
			filesystem.remove(path)


# ------------------------------------------------------------------------------------------------------------------- #
def main():
	import vsdbg
	vsdbg._attach(False)

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
def add_media(title, imdb, settings):
	ended_path = filesystem.join(addon_data_path(), imdb + '.ended')
	if filesystem.exists(ended_path):
		try:
			filesystem.remove(ended_path)
		except: pass

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

	import xbmcgui
	from settings import _addon_name

	class RemoteDialogProgress(xbmcgui.DialogProgressBG):

		def __init__(self, *args, **kwargs):
			self.progress_file_path = filesystem.join(addon_data_path(), '.'.join([imdb, 'progress']))
			return super(RemoteDialogProgress, self).__init__(*args, **kwargs)

		def Refresh(self):
			if filesystem.exists(self.progress_file_path):
				try:
					try:
						with filesystem.fopen(self.progress_file_path, 'r') as progress_file:
							args = progress_file.read().split('\n')
					except:
						args = [0]

					args[0] = int(args[0])
					self.update(*args)
				except: pass

	info_dialog = RemoteDialogProgress()
	info_dialog.create(_addon_name)
	
	strm_path = filesystem.join(addon_data_path(), imdb + '.strm_path')
	for cnt in range(300):
		info_dialog.Refresh()
		#---------------------------------
		"""
		if filesystem.exists(strm_path):
			with filesystem.fopen(strm_path, 'r') as f:
				source = f.read()	# utf-8
				if source and source.endswith('.strm'):
					strm_path = filesystem.join(settings.base_path(), source)
					if filesystem.exists(strm_path):
						with filesystem.fopen(strm_path, 'r') as strm:
							url = strm.read()
							xbmc.executebuiltin('RunPlugin("%s")' % url)
		"""
		#---------------------------------
		if filesystem.exists(ended_path):
			with filesystem.fopen(ended_path, 'r') as f:
				dlg = xbmcgui.Dialog()

				count = f.read()
				try: 
					count = int(count)
				except ValueError: count = 0

				if not xbmc.Player().isPlaying():
					if count:
						dlg.notification(_addon_name, u'"%s" добавлено в библиотеку, найдено %d источников.' % (title, count), time=10000)

						xbmc.executebuiltin('Container.Refresh')

						url = 'plugin://script.media.aggregator/?' + urllib.urlencode(
							{'action': 'add_media',
								'title': title.encode('utf-8'),
								'imdb': imdb,
								'strm': strm_path.encode('utf-8'),
								'norecursive': True})

						xbmc.executebuiltin('RunPlugin("%s")' % url)
					else:
						dlg.notification(_addon_name,
											u'"%s" не добавлено в библиотеку, Источники не найдены.' % title,
											time=10000)
			try:
				filesystem.remove(ended_path)
			except: pass

			break

		sleep(1)

	info_dialog.close()

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
	path = filesystem.join(_addondir, 'version_latest')
	if not filesystem.exists(path):
		try:
			with filesystem.fopen(path, 'w') as f:
				f.write('test')

			if filesystem.exists(path):
				url = 'https://github.com/vadyur/script.media.aggregator/releases/download/ver_0.15.2/version_latest'
				response = urllib2.urlopen(url)
				log.debug(response.read())
		except BaseException as e:
			log.print_tb(e)
			pass


# ------------------------------------------------------------------------------------------------------------------- #
if __name__ == '__main__':
	try:
		create_mark_file()
		save_dbs()
	except BaseException as e:
		log.print_tb(e)
		pass

	main()
