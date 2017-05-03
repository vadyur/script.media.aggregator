_debug = False

def _bp(wait=True):
	if not _debug:
		return

	try:
		import random, os
		port = random.randint(6600, 6800)

		import ptvsd
		ptvsd.enable_attach(secret = None, address = ('0.0.0.0', port))

		cmd = "tcp://localhost:%d" % port
		#print "%s  for attach to debugger" % cmd

		os.system('echo ' + cmd + '| clip')

		if wait:
			ptvsd.wait_for_attach()

		pass
	
	except:
		pass
