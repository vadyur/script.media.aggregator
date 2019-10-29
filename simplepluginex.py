from simpleplugin import SimplePluginError, Storage, MemStorage, Addon, Plugin, Params, debug_exception

from urlparse import parse_qs
from urllib import urlencode
import codecs


class PluginEx(Plugin):
	
	@staticmethod
	def get_params(paramstring):
		"""
		Convert a URL-encoded paramstring to a Python dict

		:param paramstring: URL-encoded paramstring
		:type paramstring: str
		:return: parsed paramstring
		:rtype: Params
		"""
		raw_params = parse_qs(paramstring)
		params = Params()
		for key, value in raw_params.iteritems():
			params[key] = value[0] if len(value) == 1 else value
			if isinstance(params[key], str) and params[key].startswith(codecs.BOM_UTF8):
				params[key] = params[key].decode('utf-8-sig')
		return params

	def get_url(self, plugin_url='', **kwargs):
		"""
		Construct a callable URL for a virtual directory item

		If plugin_url is empty, a current plugin URL is used.
		kwargs are converted to a URL-encoded string of plugin call parameters
		To call a plugin action, 'action' parameter must be used,
		if 'action' parameter is missing, then the plugin root action is called
		If the action is not added to :class:`Plugin` actions, :class:`PluginError` will be raised.

		:param plugin_url: plugin URL with trailing / (optional)
		:type plugin_url: str
		:param kwargs: pairs of key=value items
		:return: a full plugin callback URL
		:rtype: str
		"""
		url = plugin_url or self._url
		if kwargs:
			def to_u8bom(v):
				if isinstance(v, unicode):
					v = v.encode('utf-8-sig')
				return v

			kwargs_ = { k: to_u8bom(v) for k, v in kwargs.items() }
		
			return '{0}?{1}'.format(url, urlencode(kwargs_, doseq=True))
		return url
