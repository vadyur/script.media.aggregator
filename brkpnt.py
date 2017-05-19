_debug = True

import subprocess

def write_to_clipboard(output):
    process = subprocess.Popen(
        'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))

def read_from_clipboard():
    return subprocess.check_output(
        'pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')

def _bp(wait=True):
	if not _debug:
		return

	try:
		import random, os
		port = random.randint(6600, 6800)

		import ptvsd
		ptvsd.enable_attach(secret = None, address = ('0.0.0.0', port))

		import platform

		cmd = "tcp://localhost:%d" % port
		if platform.system() == 'Windows':
			os.system('echo ' + cmd + '| clip')
		elif platform.system() == 'Darwin':
			cmd = "tcp://vd-mac:%d" % port
			write_to_clipboard(cmd)
		else:
			print platform.system() + ' no detect, cmd = ' + cmd

		if wait:
			ptvsd.wait_for_attach()

		pass
	
	except:
		pass
