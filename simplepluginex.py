from simpleplugin import SimplePluginError, Storage, Addon, Plugin, Params

import codecs

class PluginEx(Plugin):
	
	@staticmethod
	def get_params(paramstring):
		params = Plugin.get_params(paramstring)
		for key, value in params.items():
			if isinstance(value, str) and value.startswith(codecs.BOM_UTF8):
				params[key] = value.decode('utf-8-sig')
		return params

	def get_url(self, plugin_url='', **kwargs):
		def to_u8bom(v):
			if isinstance(v, unicode):
				v = v.encode('utf-8-sig')
			return v

		kwargs_ = { k: to_u8bom(v) for k, v in kwargs.items() }
		return Plugin.get_url(self, plugin_url, **kwargs_)
