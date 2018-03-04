# -*- coding: utf-8 -*-

class soup_base(object):
	def __init__(self, url, headers=None):
		self.url = url
		self._soup = None
		self._request = None
		self._headers = headers

	@property
	def soup(self):
		if not self._soup:
			import requests
			from bs4 import BeautifulSoup
			r = requests.get(self.url, headers=self._headers)
			self._soup = BeautifulSoup(r.content, 'html.parser')
			self._request = r

		return self._soup
