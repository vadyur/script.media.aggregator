import urllib, sys

def make_url(params):
	url = 'plugin://script.media.aggregator/?' + urllib.urlencode(params)
	return url

def get_params():
	if len(sys.argv) < 3:
		return None

	param = dict()

	paramstring = sys.argv[2]
	if len(paramstring) >= 2:
		params = sys.argv[2]
		cleanedparams = params.replace('?', '')
		if (params[len(params) - 1] == '/'):
			params = params[0:len(params) - 2]
		pairsofparams = cleanedparams.split('&')
		param = {}
		for i in range(len(pairsofparams)):
			splitparams = {}
			splitparams = pairsofparams[i].split('=')
			if (len(splitparams)) == 2:
				param[splitparams[0]] = splitparams[1]

	# debug(param)
	return param
