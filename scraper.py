import binascii, socket, random, struct
import urllib.parse, urllib.request
from urllib.parse import urlparse, urlunsplit
from typing import Dict, List, Tuple

from vdlib.util.log import debug
from vdlib.torrent.bencodepy import bdecode

ScrapeResult = Dict[str, Dict[str, int]]


def scrape(tracker: str, hashes: List[str], timeout: float = 1) -> ScrapeResult:
	"""
	Returns the list of seeds, peers and downloads a torrent info_hash has, according to the specified tracker

	Args:
		tracker (str): The announce url for a tracker, usually taken directly from the torrent metadata
		hashes (list): A list of torrent info_hash's to query the tracker for

	Returns:
		A dict of dicts. The key is the torrent info_hash's from the 'hashes' parameter,
		and the value is a dict containing "seeds", "peers" and "complete".
		Eg:
		{
			"2d88e693eda7edf3c1fd0c48e8b99b8fd5a820b2" : { "seeds" : 34, "peers" : 189, "complete" : 10 },
			"8929b29b83736ae650ee8152789559355275bd5c" : { "seeds" : 12, "peers" : 0, "complete" : 290 }
		}
	"""
	tracker = tracker.lower()
	parsed = urlparse(tracker)
	if parsed.scheme == "udp":
		return scrape_udp(parsed, hashes, timeout)

	if parsed.scheme in ["http", "https"]:
		if "announce" not in tracker:
			raise RuntimeError("%s doesnt support scrape" % tracker)
		parsed = urlparse(tracker.replace("announce", "scrape"))
		return scrape_http(parsed, hashes, timeout)

	raise RuntimeError("Unknown tracker scheme: %s" % parsed.scheme)

def scrape_udp(parsed_tracker, hashes: List[str], timeout: float) -> ScrapeResult:
	debug("Scraping UDP: %s for %s hashes" % (parsed_tracker.geturl(), len(hashes)))
	if len(hashes) > 74:
		raise RuntimeError("Only 74 hashes can be scraped on a UDP tracker due to UDP limitations")
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.settimeout(timeout)
	try:
		conn = (socket.gethostbyname(parsed_tracker.hostname), parsed_tracker.port)

		#Get connection ID
		req, transaction_id = udp_create_connection_request()
		sock.sendto(req, conn)
		buf = sock.recvfrom(2048)[0]
		connection_id = udp_parse_connection_response(buf, transaction_id)

		#Scrape away
		req, transaction_id = udp_create_scrape_request(connection_id, hashes)
		sock.sendto(req, conn)
		buf = sock.recvfrom(2048)[0]
		return udp_parse_scrape_response(buf, transaction_id, hashes)
	finally:
		sock.close()

def scrape_http(parsed_tracker, hashes: List[str], timeout: float) -> ScrapeResult:
	debug("Scraping HTTP: %s for %s hashes" % (parsed_tracker.geturl(), len(hashes)))
	qs = urllib.parse.urlencode([("info_hash", binascii.a2b_hex(h)) for h in hashes])
	pt = parsed_tracker
	url = urlunsplit((pt.scheme, pt.netloc, pt.path, qs, pt.fragment))
	debug(url)
	try:
		handle = urllib.request.urlopen(url, timeout=timeout)
	except BaseException:
		raise RuntimeError("Timeout")

	if handle.getcode() != 200:
		raise RuntimeError("%s status code returned" % handle.getcode())

	decoded = bdecode(handle.read())
	ret = {}  # type: ScrapeResult
	for hash, stats in decoded.get(b'files', {}).items():
		nice_hash = binascii.b2a_hex(hash).decode('ascii')
		try:
			s = stats.get(b"complete", -1)
			p = stats.get(b"incomplete", -1)
			c = stats.get(b"downloaded", -1)
			ret[nice_hash] = { "seeds" : s, "peers" : p, "complete" : c}
		except BaseException as e:
			debug(str(e))
	return ret

def udp_create_connection_request() -> Tuple[bytes, int]:
	connection_id = 0x41727101980 #default connection id
	action = 0x0 #action (0 = give me a new connection id)
	transaction_id = udp_get_transaction_id()
	buf = struct.pack("!q", connection_id) #first 8 bytes is connection id
	buf += struct.pack("!i", action) #next 4 bytes is action
	buf += struct.pack("!i", transaction_id) #next 4 bytes is transaction id
	return (buf, transaction_id)

def udp_parse_connection_response(buf: bytes, sent_transaction_id: int) -> int:
	if len(buf) < 16:
		raise RuntimeError("Wrong response length getting connection id: %s" % len(buf))
	action = struct.unpack_from("!i", buf)[0] #first 4 bytes is action

	res_transaction_id = struct.unpack_from("!i", buf, 4)[0] #next 4 bytes is transaction id
	if res_transaction_id != sent_transaction_id:
		raise RuntimeError("Transaction ID doesnt match in connection response! Expected %s, got %s"
			% (sent_transaction_id, res_transaction_id))

	if action == 0x0:
		return struct.unpack_from("!q", buf, 8)[0] #unpack 8 bytes from byte 8, should be the connection_id
	elif action == 0x3:
		error = buf[8:].decode('utf-8', 'replace')
		raise RuntimeError("Error while trying to get a connection response: %s" % error)
	raise RuntimeError("Unknown action in connection response: %s" % action)

def udp_create_scrape_request(connection_id: int, hashes: List[str]) -> Tuple[bytes, int]:
	action = 0x2 #action (2 = scrape)
	transaction_id = udp_get_transaction_id()
	buf = struct.pack("!q", connection_id) #first 8 bytes is connection id
	buf += struct.pack("!i", action) #next 4 bytes is action
	buf += struct.pack("!i", transaction_id) #followed by 4 byte transaction id
	#from here on, there is a list of info_hashes. They are packed as char[]
	for hash in hashes:
		buf += struct.pack("!20s", binascii.a2b_hex(hash))
	return (buf, transaction_id)

def udp_parse_scrape_response(buf: bytes, sent_transaction_id: int, hashes: List[str]) -> ScrapeResult:
	if len(buf) < 16:
		raise RuntimeError("Wrong response length while scraping: %s" % len(buf))
	action = struct.unpack_from("!i", buf)[0] #first 4 bytes is action
	res_transaction_id = struct.unpack_from("!i", buf, 4)[0] #next 4 bytes is transaction id
	if res_transaction_id != sent_transaction_id:
		raise RuntimeError("Transaction ID doesnt match in scrape response! Expected %s, got %s"
			% (sent_transaction_id, res_transaction_id))
	if action == 0x2:
		ret = {}  # type: ScrapeResult
		offset = 8 #next 4 bytes after action is transaction_id, so data doesnt start till byte 8
		for hash in hashes:
			seeds = struct.unpack_from("!i", buf, offset)[0]
			offset += 4
			complete = struct.unpack_from("!i", buf, offset)[0]
			offset += 4
			leeches = struct.unpack_from("!i", buf, offset)[0]
			offset += 4
			ret[hash] = { "seeds" : seeds, "peers" : leeches, "complete" : complete }
		return ret
	elif action == 0x3:
		#an error occured, try and extract the error string
		error = buf[8:].decode('utf-8', 'replace')
		raise RuntimeError("Error while scraping: %s" % error)
	raise RuntimeError("Unknown action in scrape response: %s" % action)

def udp_get_transaction_id() -> int:
	return int(random.randrange(0, 255))
