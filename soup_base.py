# -*- coding: utf-8 -*-

class soup_base(object):
	_soups = {}

	def __init__(self, url, headers=None):
		self.url = url
		self._soup = None
		self._headers = headers

	@property
	def soup(self):
		if not self._soup:
			if self.url in self._soups:
				self._soup = self._soups[self.url]
			else:
				import requests
				from bs4 import BeautifulSoup
				r = requests.get(self.url, headers=self._headers)
				self._soup = BeautifulSoup(r.content, 'html.parser')
				self._soups[self.url] = self._soup

		return self._soup
