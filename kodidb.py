import xbmc, json, filesystem, xbmcvfs, os, re
import xml.etree.ElementTree as ET

class AdvancedSettingsReader(object):
	dict = {}
	def LOG(self, s):
		print '[AdvancedSettingsReader]: ' + s
	
	def __init__(self):
		self.use_mysql = False
		self.dict.clear()
	
		path = xbmc.translatePath('special://profile/advancedsettings.xml').decode('utf-8')
		self.LOG(path)
		if not filesystem.exists(path):
			return

		try:
			with filesystem.fopen(path, 'r') as f:
				content = f.read()
				root = ET.fromstring(content)
		except IOError as e:
			self.LOG("I/O error({0}): {1}".format(e.errno, e.strerror))

		for section in root:
			if section.tag == 'videodatabase':
				for child in section:
					if child.tag in ['type', 'host', 'port', 'user', 'pass', 'name']:
						self.dict[child.tag] = child.text
						print child.text
				self.LOG('<videodatabase> found')
				return
				
		self.LOG('<videodatabase> not found')
		
	def __getitem__(self, key):
		return self.dict.get(key, None)

reader = AdvancedSettingsReader()
		
		
BASE_PATH = 'special://database'		
class VideoDatabase(object):
	@staticmethod
	def find_last_version(name):
		dirs, files = xbmcvfs.listdir(BASE_PATH)
		matched_files = [f for f in files if f.startswith(name)]
		versions = [int(os.path.splitext(f[len(name):])[0]) for f in matched_files]
		if not versions:
			return 0
		return max(versions)		

	def __init__(self):
		try:
			
			self.DB_NAME = reader['name'] if reader['name'] is not None else 'myvideos93'
			self.DB_USER = reader['user']
			self.DB_PASS = reader['pass']
			self.DB_ADDRESS = reader['host'] #+ ':' + reader['port']
			self.DB_PORT=reader['port']
		  
			if reader['type'] == 'mysql' and \
							self.DB_ADDRESS is not None and \
							self.DB_USER is not None and \
							self.DB_PASS is not None and \
							self.DB_NAME is not None:
		  
				xbmc.log('kodidb: Service: Loading MySQL as DB engine')
				self.DB = 'mysql'
			else:
				xbmc.log('kodidb: Service: MySQL not enabled or not setup correctly')
				raise ValueError('MySQL not enabled or not setup correctly')
		except:
			self.DB = 'sqlite'
			self.db_dir = os.path.join(xbmc.translatePath(BASE_PATH), 'MyVideos%s.db' % VideoDatabase.find_last_version('MyVideos'))
			
	def create_connection(self):
		if self.DB == 'mysql':
			import mysql.connector
			return mysql.connector.connect(	database=self.DB_NAME, \
											user=self.DB_USER, \
											password=self.DB_PASS, \
											host=self.DB_ADDRESS, \
											port=self.DB_PORT, \
											buffered=True)
		else:
			from sqlite3 import dbapi2 as db_sqlite
			return db_sqlite.connect(self.db_dir)
			
	def sql_request(self, req):
		if self.DB == 'mysql':
			return req.replace('?', '%s')
		else:
			return req.replace('%s', '?')
	
class KodiDB(object):
	
	def debug(self, msg):
		if isinstance(msg, unicode):
			msg = msg.encode('utf-8')
		print '[KodiDB] %s' % msg
	
	def __init__(self, strmName, strmPath, pluginUrl):
		
		self.debug('strmName: ' + strmName)
		self.debug('strmPath: ' + strmPath)
		self.debug('pluginUrl: ' + pluginUrl)
		
		self.timeOffset	= 0
		
		self.strmName 	= strmName
		self.strmPath 	= strmPath
		self.pluginUrl 	= pluginUrl
		
		self.videoDB = VideoDatabase()
	
	def PlayerPreProccessing(self):
		xbmc.sleep(1000)
		self.db = self.videoDB.create_connection()
		try:
			self.debug('PlayerPreProccessing: ')
			strmItem = self.getFileItem(self.strmName, self.strmPath)
			print strmItem
			bookmarkItem = self.getBookmarkItem(strmItem['idFile'])
			print bookmarkItem
			self.timeOffset = bookmarkItem['timeInSeconds'] if bookmarkItem != None else 0
			self.debug('timeOffset: ' + str(self.timeOffset / 60) )
		finally:
			self.db.close()
	
	def PlayerPostProccessing(self):
		self.db = self.videoDB.create_connection()
		try:
			pluginItem = self.getFileItem(self.pluginUrl)
			print pluginItem
			strmItem = self.getFileItem(self.strmName, self.strmPath)
			print strmItem
			
			self.CopyWatchedStatus(pluginItem, strmItem)
			self.ChangeBookmarkId(pluginItem, strmItem)

		finally:
			self.db.close()
		
		
	def CopyWatchedStatus(self, pluginItem, strmItem ):
	
		if pluginItem['playCount'] is None or strmItem['idFile'] is None:
			return
		
		cur = self.db.cursor()

		sql = 	'UPDATE files'
		sql += 	' SET playCount=' + str(pluginItem['playCount'])
		sql += 	' WHERE idFile LIKE ' + str(strmItem['idFile'])
		
		self.debug('CopyWatchedStatus: ' + sql)
		
		cur.execute(sql)
		self.db.commit()
		
	def ChangeBookmarkId(self, pluginItem, strmItem ):
		if strmItem['idFile'] is None or pluginItem['idFile'] is None:
			return
	
		cur = self.db.cursor()

		sql =  'UPDATE bookmark SET idFile=' + str(strmItem['idFile'])
		sql += ' WHERE idFile LIKE ' +  str(pluginItem['idFile'])
		self.debug('ChangeBookmarkId: ' + sql)
		
		cur.execute(sql)
		self.db.commit()
		
	def getBookmarkItem(self, idFile):
		cur = self.db.cursor()
		sql =	"SELECT idBookmark, idFile, timeInSeconds, totalTimeInSeconds " + \
				"FROM bookmark WHERE idFile LIKE " + str(idFile)
		cur.execute(sql)
		bookmarks = cur.fetchall()
		for item in bookmarks:
			self.debug('Bookmark: ' + item.__repr__())
			return { 'idBookmark': item[0], 'idFile': item[1], 'timeInSeconds': item[2], 'totalTimeInSeconds': item[3] }
		
	def getFileItem(self, strFilename, strPath = None):
		cur = self.db.cursor()
		
		sql = 	"SELECT idFile, idPath, strFilename, playCount, lastPlayed " + \
				"FROM files WHERE strFilename " + \
				"LIKE '" + strFilename.split('&nfo=')[0] + "%'"
		cur.execute(sql)
		files = cur.fetchall()
		
		if len(files) == 0:
			print 'len(files) == 0'
			return None

		if strPath is None:
			for item in files:
				self.debug('File: ' + item.__repr__())
				return { 'idFile': item[0], 'idPath': item[1], 'strFilename': item[2], 'playCount': item[3], 'lastPlayed': item[4] }
		else:
			sql = 'SELECT idPath, strPath FROM path WHERE idPath IN ( '
			ids = []
			for item in files:
				ids.append( str( item[1]))
			sql += ', '.join(ids) + ' )'
			print sql
			cur.execute(sql)
			paths = cur.fetchall()
			for path in paths:
				#pattern = path[1].replace('\\', '/').replace('[', '\\[').replace(']', '\\]')
				if path[1].replace('\\', '/').endswith(strPath + '/') or path[1].replace('/', '\\').endswith(strPath + '\\'):
					for item in files:
						if path[0] == item[1]:
							self.debug('File: ' + item.__repr__())
							return { 'idFile': item[0], 'idPath': item[1], 'strFilename': item[2], 'playCount': item[3], 'lastPlayed': item[4] }
		
		print 'return None'
		return None
		
	def getPathId(self, strPath):
		cur = self.db.cursor()
		
		sql = 	"SELECT idPath, strPath FROM path " + \
				"WHERE strPath LIKE '%" + strPath.encode('utf-8') + "%'"
		print sql
		cur.execute(sql)
		return cur.fetchall()
		
	def getFileDataById(self, fileId):
		return
		
		
