import log

import filesystem, os, time
import xml.etree.ElementTree as ET

test_reader = None

class AdvancedSettingsReader(object):
	dict = {}
	def LOG(self, s):
		log.debug('[AdvancedSettingsReader]: ' + s)
	
	def __init__(self):
		self.use_mysql = False
		self.dict.clear()
		root = []
	
		try:
			import xbmc
			path = xbmc.translatePath('special://profile/advancedsettings.xml').decode('utf-8')
			self.LOG(path)
			if filesystem.exists(path):
				self.load(path)
		except:
			pass

	def load(self, path):
		try:
			with filesystem.fopen(path, 'r') as f:
				content = f.read()
				#log.debug(content)
				root = ET.fromstring(content)
		except IOError as e:
			self.LOG("I/O error({0}): {1}".format(e.errno, e.strerror))
			return
		except BaseException as e:
			self.LOG("error: " + str(e))
			return

		for section in root:
			if section.tag == 'videodatabase':
				for child in section:
					if child.tag in ['type', 'host', 'port', 'user', 'pass', 'name']:
						self.dict[child.tag] = child.text
						log.debug(child.text)
				self.LOG('<videodatabase> found')
				return
				
		self.LOG('<videodatabase> not found')
		
	def __getitem__(self, key):
		return self.dict.get(key, None)

DB_VERSIONS = {
	'10': '37',
	'11': '60',
	'12': '75',
	'13': '78',
	'14': '90',
	'15': '93',
	'16': '99',
	'17': '107'
}

BASE_PATH = 'special://database'		
class VideoDatabase(object):
	@staticmethod
	def find_last_version(name, path=BASE_PATH):
		import re, filesystem
		try:
			if path.startswith('special://'):
				import xbmc
				path = xbmc.translatePath(path)
			files = filesystem.listdir(path)
			matched_files = [f for f in files if bool(re.match(name, f, re.I))]  #f.startswith(name)]
			versions = [int(os.path.splitext(f[len(name):])[0]) for f in matched_files]
			if not versions:
				return 0
			return max(versions)
		except BaseException as e:
			log.debug(e, log.lineno())
			raise ValueError('find_last_version not detect')

	@staticmethod
	def get_db_version(name=None):
		try:
			import xbmc		
			major = xbmc.getInfoLabel("System.BuildVersion").split(".")[0]
			ver = DB_VERSIONS.get(major)
			if ver:
				return ver

			return VideoDatabase.find_last_version(name, 'special://home/dbversions')
		except (ImportError, ValueError):
			return DB_VERSIONS['17']

	def __init__(self):
		try:
			reader = test_reader if test_reader else AdvancedSettingsReader()
			
			self.DB_NAME = reader['name'] if reader['name'] is not None else 'MyVideos'
			self.DB_NAME += self.get_db_version(self.DB_NAME)
			log.debug('kodidb: DB name is ' + self.DB_NAME )

			self.DB_USER = reader['user']
			self.DB_PASS = reader['pass']
			self.DB_ADDRESS = reader['host']
			self.DB_PORT=reader['port']

			if reader['type'] == 'mysql' and \
							self.DB_ADDRESS is not None and \
							self.DB_USER is not None and \
							self.DB_PASS is not None and \
							self.DB_NAME is not None:

				log.debug('kodidb: Service: Loading MySQL as DB engine')
				self.DB = 'mysql'
			else:
				log.debug('kodidb: Service: MySQL not enabled or not setup correctly')
				raise ValueError('MySQL not enabled or not setup correctly')
		except:
			self.DB = 'sqlite'
			import xbmc
			db_path = xbmc.translatePath(BASE_PATH)
			self.db_dir = filesystem.join(db_path, 'MyVideos%s.db' % VideoDatabase.find_last_version('MyVideos', db_path))
			
	def create_connection(self):
		if self.DB == 'mysql':
			import mysql.connector
			return mysql.connector.connect(	database=self.DB_NAME,
											user=self.DB_USER,
											password=self.DB_PASS,
											host=self.DB_ADDRESS,
											port=self.DB_PORT,
											buffered=True)
		else:
			from sqlite3 import dbapi2 as db_sqlite
			return db_sqlite.connect(self.db_dir)
			
	def sql_request(self, req):
		if self.DB == 'mysql':
			return req.replace('?', '%s')
		else:
			return req.replace('%s', '?')

def request(fn):
	def wrapper(self, *args, **kwargs):
		self.db = self.videoDB.create_connection()
		try:
			sql = fn(self, *args, **kwargs)

			cur = self.db.cursor()
			cur.execute(sql)
			result = cur.fetchall()
			self.db.commit()

			#result = []
			#for item in res:
			#	result.append(item)
			return result
	
		except BaseException as e:
			pass

		finally:
			self.db.close()
	
	return wrapper

def request_dict(fn):
	def wrapper(self, *args, **kwargs):
		self.db = self.videoDB.create_connection()
		try:
			sql = fn(self, *args, **kwargs)

			cur = self.db.cursor()
			cur.execute(sql)
			result = cur.fetchall()
			self.db.commit()

			keys = sql.replace('select', '')
			keys = keys.split('from')[0]
			keys = keys.split(',')
			keys = [ k.strip() for k in keys ]

			out = []
			for res in result:
				dct = {}
				for i, k in enumerate(keys):
					dct[k.strip()] = res[i]
				out.append(dct.copy())

			return out

		finally:
			self.db.close()
	
	return wrapper

class KodiDB(object):
	
	def debug(self, msg, line=0):
		if isinstance(msg, unicode):
			msg = msg.encode('utf-8')
		#line = inspect.currentframe().f_back.f_back.f_lineno
		log.debug('[KodiDB:%d] %s' % (line, msg))
	
	def __init__(self, strmName, strmPath, pluginUrl):
		
		self.debug('strmName: ' + strmName, log.lineno())
		self.debug('strmPath: ' + strmPath, log.lineno())
		self.debug('pluginUrl: ' + pluginUrl, log.lineno())
		
		self.timeOffset	= 0
		
		self.strmName 	= strmName
		self.strmPath 	= strmPath
		self.pluginUrl 	= pluginUrl
		
		self.videoDB = VideoDatabase()
	
	def PlayerPreProccessing(self):
		import xbmc
		xbmc.sleep(1000)
		self.db = self.videoDB.create_connection()
		try:
			self.debug('PlayerPreProccessing: ', log.lineno())
			strmItem = self.getFileItem(self.strmName, self.strmPath)
			if not strmItem is None:
				self.debug('\tstrmItem = ' + str(strmItem), log.lineno())
				bookmarkItem = self.getBookmarkItem(strmItem['idFile'])
				self.debug('\tbookmarkItem = ' + str(bookmarkItem), log.lineno())
				self.timeOffset = bookmarkItem['timeInSeconds'] if bookmarkItem != None else 0
				self.debug('\ttimeOffset: ' + str(self.timeOffset / 60) , log.lineno())
			else:
				self.debug('\tstrmItem is None', log.lineno())
		finally:
			self.db.close()
	
	def PlayerPostProccessing(self):
		self.db = self.videoDB.create_connection()
		try:
			self.debug('PlayerPostProccessing: ', log.lineno())

			for cnt in range(3):
				pluginItem = self.getFileItem(self.pluginUrl)
				self.debug('\tpluginItem = ' + str(pluginItem), log.lineno())

				if pluginItem:
					break

				self.debug('Try again #' + str(cnt + 2))
				time.sleep(2)

			strmItem = self.getFileItem(self.strmName, self.strmPath)
			self.debug('\tstrmItem = ' + str(strmItem), log.lineno())
			
			self.CopyWatchedStatus(pluginItem, strmItem)
			self.ChangeBookmarkId(pluginItem, strmItem)

		finally:
			self.db.close()
		
	def CopyWatchedStatus(self, pluginItem, strmItem ):
	
		if pluginItem is None or strmItem is None:
			return

		if pluginItem['playCount'] is None or strmItem['idFile'] is None:
			return
		
		cur = self.db.cursor()

		sql = 	'UPDATE files'
		sql += 	' SET playCount=' + str(pluginItem['playCount'])
		sql += 	' WHERE idFile = ' + str(strmItem['idFile'])
		
		self.debug('CopyWatchedStatus: ' + sql, log.lineno())
		
		cur.execute(sql)
		self.db.commit()
		
	def ChangeBookmarkId(self, pluginItem, strmItem ):
		if pluginItem is None or strmItem is None:
			return
			
		if strmItem['idFile'] is None or pluginItem['idFile'] is None:
			return
	
		cur = self.db.cursor()
		
		#delete previous
		sql = "DELETE FROM bookmark WHERE idFile=" + str(strmItem['idFile'])
		self.debug('ChangeBookmarkId: ' + sql, log.lineno())
		cur.execute(sql)
		self.db.commit()
		

		#set new
		sql =  'UPDATE bookmark SET idFile=' + str(strmItem['idFile'])
		sql += ' WHERE idFile = ' +  str(pluginItem['idFile'])
		self.debug('ChangeBookmarkId: ' + sql, log.lineno())
		
		cur.execute(sql)
		self.db.commit()
		
	def getBookmarkItem(self, idFile):
		cur = self.db.cursor()
		sql =	"SELECT idBookmark, idFile, timeInSeconds, totalTimeInSeconds " + \
				"FROM bookmark WHERE idFile = " + str(idFile)
		cur.execute(sql)
		bookmarks = cur.fetchall()
		for item in bookmarks:
			self.debug('Bookmark: ' + item.__repr__(), log.lineno())
			return { 'idBookmark': item[0], 'idFile': item[1], 'timeInSeconds': item[2], 'totalTimeInSeconds': item[3] }
			
		return None
		
	def getFileItem(self, strFilename, strPath = None):
		cur = self.db.cursor()
		
		sql = 	"SELECT idFile, idPath, strFilename, playCount, lastPlayed " + \
				"FROM files WHERE strFilename" + \
				"='" + strFilename.replace("'", "''")	+ "'" #.split('&nfo=')[0] + "%'"
		self.debug(sql, log.lineno())
		cur.execute(sql)
		files = cur.fetchall()
		
		if len(files) == 0:
			self.debug('getFileItem: len(files) == 0', log.lineno())
			return None

		if strPath is None:
			for item in files:
				self.debug('File: ' + item.__repr__(), log.lineno())
				return { 'idFile': item[0], 'idPath': item[1], 'strFilename': item[2], 'playCount': item[3], 'lastPlayed': item[4] }
		else:
			sql = 'SELECT idPath, strPath FROM path WHERE idPath IN ( '
			ids = []
			for item in files:
				ids.append( str( item[1]))
			sql += ', '.join(ids) + ' )'
			self.debug(sql, log.lineno())
			cur.execute(sql)
			paths = cur.fetchall()
			for path in paths:
				#pattern = path[1].replace('\\', '/').replace('[', '\\[').replace(']', '\\]')
				if path[1].replace('\\', '/').endswith(strPath + '/') or path[1].replace('/', '\\').endswith(strPath + '\\'):
					for item in files:
						if path[0] == item[1]:
							self.debug('File: ' + item.__repr__(), log.lineno())
							return { 'idFile': item[0], 'idPath': item[1], 'strFilename': item[2], 'playCount': item[3], 'lastPlayed': item[4] }
		
		self.debug('return None', log.lineno())
		return None
		
	def getPathId(self, strPath):
		cur = self.db.cursor()
		
		sql = 	"SELECT idPath, strPath FROM path " + \
				"WHERE strPath LIKE '%" + strPath.encode('utf-8').replace("'", "''") + "%'"
		self.debug(sql, log.lineno())
		cur.execute(sql)
		return cur.fetchall()
		
	def getFileDataById(self, fileId):
		return

class MoreRequests(object):

	_videoDB = None

	@property
	def videoDB(self):
		if not self._videoDB:
			self._videoDB = VideoDatabase()
		return self._videoDB

	@request_dict
	def get_movies_by_imdb(self, imdb):
		""" return movie data by imdb """

		sql = """select idMovie, idFile, c00, c22, uniqueid_value, c16, premiered, playCount, lastPlayed, resumeTimeInSeconds, totalTimeInSeconds
				from movie_view
				where uniqueid_value='{}'""".format(imdb)
		self._log(sql)
		return sql

	def _log(self, s):
		from log import debug
		debug('MoreRequests: {}'.format(s))

	@request
	def update_movie_by_id(self, id, fields={}):
		try:
			expression = ''
			for k, v in fields.iteritems():
				if isinstance(v, unicode):
					v = v.encode('utf-8')
				expression += "{}='{}', ".format(k, v.replace("'", "''"))

			sql = """UPDATE movie_view
					SET {}
					WHERE idMovie='{}'""".format(expression[:-2], id)
			self._log(sql)
			return sql
		except BaseException as e:
			pass

	@request
	def remove_movie_by_id(self, id):
		sql = """DELETE FROM table_name
				WHERE idMovie='{}'""".format(id)
		self._log(sql)
		return sql
		
	@request
	def get_movie_duplicates(self):
		sql = """SELECT idMovie, idFile, c00, c22, uniqueid_value, COUNT(uniqueid_value)
				FROM movie_view
				WHERE uniqueid_value like 'tt%'
				GROUP BY
				    uniqueid_value
				HAVING 
				    COUNT(uniqueid_value) > 1"""
		self._log(sql)
		return sql

def wait_for_update():
	try:
		import xbmc
		count = 1000
		while not xbmc.abortRequested and xbmc.getCondVisibility('Library.IsScanningVideo') and count:
			log.debug('Library Scanning Video - wait')
			xbmc.sleep(100)
			count -= 1
	except:
		import time
		time.sleep(1)
