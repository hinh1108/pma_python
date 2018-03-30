from os import path
from math import ceil
from PIL import Image
from random import choice
from io import BytesIO
from urllib.parse import quote
from urllib.request import urlopen
from xml.dom import minidom

import requests

__version__ = "2.0.0.0"

# internal module helper variables and functions
_pma_sessions = dict()
_pma_slideinfos = dict()
_pma_pmacoreliteURL = "http://localhost:54001/"
_pma_pmacoreliteSessionID = "SDK.Python"

def _pma_session_id(sessionID = None):
	if (sessionID is None):
		# if the sessionID isn't specified, maybe we can still recover it somehow
		return _pma_first_session_id()
	else:
		# nothing to do in this case; a SessionID WAS passed along, so just continue using it
		return sessionID
		
def _pma_first_session_id():
	# do we have any stored sessions from earlier login events?
	global _pma_sessions
	global _pma_slideinfos
	
	if (len(_pma_sessions.keys()) > 0):
		# yes we do! This means that when there's a PMA.core active session AND PMA.core.lite version running, 
		# the PMA.core active will be selected and returned
		return list(_pma_sessions.keys())[0]
	else:
		# ok, we don't have stored sessions; not a problem per se...
		if (_pma_is_lite()):
			if (not _pma_pmacoreliteSessionID in _pma_slideinfos):
				# _pma_sessions[_pma_pmacoreliteSessionID] = _pma_pmacoreliteURL
				
				_pma_slideinfos[_pma_pmacoreliteSessionID] = dict()
			return _pma_pmacoreliteSessionID
		else:
			# no stored PMA.core sessions found NOR PMA.core.lite
			return None
	
def _pma_url(sessionID = None):	
	sessionID = _pma_session_id(sessionID)
	if sessionID is None:
		# sort of a hopeless situation; there is no URL to refer to
		return None
	elif sessionID == _pma_pmacoreliteSessionID:
		return _pma_pmacoreliteURL
	else:
		# assume sessionID is a valid session; otherwise the following will generate an error
		url = _pma_sessions[sessionID]
		if (not url.endswith("/")):
			url = url + "/"
		return url

def _pma_is_lite(pmacoreURL = _pma_pmacoreliteURL):
	url = _pma_join(pmacoreURL, "api/xml/IsLite")
	try:
		contents = urlopen(url).read()
	except Exception as e:
		# this happens when NO instance of PMA.core is detected
		return None
	dom = minidom.parseString(contents)	
	return str(dom.firstChild.firstChild.nodeValue).lower() == "true"

def _pma_api_url(sessionID = None, xml = True):
	# let's get the base URL first for the specified session
	url = _pma_url(sessionID)
	if url is None:
		# sort of a hopeless situation; there is no URL to refer to
		return None
	# remember, _pma_url is guaranteed to return a URL that ends with "/"
	if (xml == True):
		return _pma_join(url, "api/xml/")
	else:
		return _pma_join(url, "api/json/")
	
def _pma_join(*s):
	joinstring = ""
	for ss in s:
		joinstring = path.join(joinstring, ss)
	return joinstring.replace("\\", "/")
	
def _pma_XmlToStringArray(root, limit = 0):
	els = root.getElementsByTagName("string")
	l = []
	if (limit > 0):
		for el in els[0: limit]:
			l.append(el.firstChild.nodeValue)
	else:
		for el in els:
			l.append(el.firstChild.nodeValue)
	return l
	
def _pma_q(arg):
	if (arg is None):
		return ''
	else:
		return quote(str(arg), safe='')
	
# end internal module helper variables and functions
	
def is_lite(pmacoreURL = _pma_pmacoreliteURL):
	"""
	See if there's a PMA.core.lite or PMA.core instance running at pmacoreURL
	"""
	return _pma_is_lite(pmacoreURL)
	
def get_version_info(pmacoreURL = _pma_pmacoreliteURL):
	"""
	Get version info from PMA.core instance running at pmacoreURL
	"""
	# purposefully DON'T use helper function _pma_api_url() here:
	# why? because GetVersionInfo can be invoked WITHOUT a valid SessionID; _pma_api_url() takes session information into account
	url = _pma_join(pmacoreURL, "api/xml/GetVersionInfo")
	try:
		contents = urlopen(url).read()
	except Exception as e:
		return None		
	dom = minidom.parseString(contents)	
	return (dom.firstChild.firstChild.nodeValue)

def connect(pmacoreURL = _pma_pmacoreliteURL, pmacoreUsername = "", pmacorePassword = ""):
	"""
	Attempt to connect to PMA.core instance; success results in a SessionID
	"""
	if (pmacoreURL == _pma_pmacoreliteURL):
		# no point authenticating localhost / PMA.core.lite
		return _pma_pmacoreliteSessionID
		
	# purposefully DON'T use helper function _pma_api_url() here:	
	# why? Because_pma_api_url() takes session information into account (which we don't have yet)
	url = _pma_join(pmacoreURL, "api/xml/authenticate?caller=SDK.Python") 
	if (pmacoreUsername != ""):
		url += "&username=" + _pma_q(pmacoreUsername)
	if (pmacorePassword != ""):
		url += "&password=" + _pma_q(pmacorePassword)
	
	contents = urlopen(url).read()
	dom = minidom.parseString(contents)
		
	loginresult = dom.firstChild
	succ = loginresult.getElementsByTagName("Success")[0]
	
	if (succ.firstChild.nodeValue.lower() == "false"):
		sessionID = None
	else:
		sessionID = loginresult.getElementsByTagName("SessionId")[0]
		sessionID = sessionID.firstChild.nodeValue
		
		global _pma_sessions
		_pma_sessions[sessionID] = pmacoreURL
		global _pma_slideinfos
		_pma_slideinfos[sessionID] = dict()
	
	return (sessionID)	

def get_root_directories(sessionID = None):
	"""
	Return an array of root-directories available to sessionID
	"""
	sessionID = _pma_session_id(sessionID)
	url = _pma_api_url(sessionID) + "GetRootDirectories?sessionID=" + _pma_q((sessionID))
	contents = urlopen(url).read()
	dom = minidom.parseString(contents)
	return _pma_XmlToStringArray(dom.firstChild)

def get_directories(startDir, sessionID = None):
	"""
	Return an array of sub-directories available to sessionID in the startDir directory
	"""
	sessionID = _pma_session_id(sessionID)
	url = _pma_api_url(sessionID) + "GetDirectories?sessionID=" + _pma_q(sessionID) + "&path=" + _pma_q(startDir)
	contents = urlopen(url).read()
	dom = minidom.parseString(contents)
	return _pma_XmlToStringArray(dom.firstChild)

def get_first_non_empty_directory(startDir = None, sessionID = None):
	sessionID = _pma_session_id(sessionID)

	if ((startDir is None) or (startDir == "")):
		startDir = "/"
	slides = get_slides(startDir, sessionID)
	if (len(slides) > 0):
		return startDir
	else:
		if (startDir == "/"):
			for dir in get_root_directories(sessionID):
				nonEmtptyDir = get_first_non_empty_directory(dir, sessionID)
				if (not (nonEmtptyDir is None)):
					return nonEmtptyDir
		else:
			for dir in get_directories(startDir, sessionID):
				nonEmtptyDir = get_first_non_empty_directory(dir, sessionID)
				if (not (nonEmtptyDir is None)):
					return nonEmtptyDir
	return None

def get_slides(startDir, sessionID = None):
	"""
	Return an array of slides available to sessionID in the startDir directory
	"""
	sessionID = _pma_session_id(sessionID)
	url = _pma_api_url(sessionID) + "GetFiles?sessionID=" + _pma_q(sessionID) + "&path=" + _pma_q(startDir)
	contents = urlopen(url).read()
	dom = minidom.parseString(contents)
	return _pma_XmlToStringArray(dom.firstChild)

def get_uid(slideRef, sessionID = None):
	"""
	Get the UID for a specific slide 
	"""
	sessionID = _pma_session_id(sessionID)
	url = _pma_api_url(sessionID) + "GetUID?sessionID=" + _pma_q(sessionID) + "&path=" + _pma_q(slideRef)
	contents = urlopen(url).read()
	dom = minidom.parseString(contents)
	return _pma_XmlToStringArray(dom)[0]
	
def who_am_i():
	"""
	Getting information about your Session (under construction)
	"""
	print ("Under construction")
	return "Under construction"
	
def sessions():
	global _pma_sessions
	return _pma_sessions

def get_tile_size(sessionID = None):
	sessionID = _pma_session_id(sessionID)
	global _pma_slideinfos
	if (len(_pma_slideinfos[sessionID]) < 1):
		dir = get_first_non_empty_directory(sessionID)
		slides = get_slides(dir, sessionID)
		info = get_slide_info(sessionID, slides[0])
	else:
		info = choice(list(_pma_slideinfos[sessionID].values()))
		
	return (int(info["TileSize"]), int(info["TileSize"]))
	
def get_slide_info(slideRef, sessionID = None):
	sessionID = _pma_session_id(sessionID)
	global _pma_slideinfos

	if (not (slideRef in _pma_slideinfos[sessionID])):
		url = _pma_api_url(sessionID, False) + "GetImageInfo?SessionID=" + _pma_q(sessionID) +  "&pathOrUid=" + _pma_q(slideRef)
		r = requests.get(url)
		_pma_slideinfos[sessionID][slideRef] = r.json()["d"]

	return _pma_slideinfos[sessionID][slideRef]

def get_max_zoomlevel(slideRef, sessionID = None):
	info = get_slide_info(slideRef, sessionID)
	if ("MaxZoomLevel" in info): 
		return int(info["MaxZoomLevel"])
	else:
		return int(info["NumberOfZoomLevels"])

def get_pixels_per_micrometer(slideRef, zoomlevel = None, sessionID = None):
	maxZoomLevel = get_max_zoomlevel(slideRef, sessionID)
	info = get_slide_info(slideRef, sessionID)
	xppm = info["MicrometresPerPixelX"]
	yppm = info["MicrometresPerPixelY"]
	if (zoomlevel is None or zoomlevel == maxZoomLevel):
		return (float(xppm), float(yppm))
	else:
		factor = 2 ** (zoomlevel - maxZoomLevel)
		return (float(xppm) / factor, float(yppm) / factor)		
	
def get_pixel_dimensions(slideRef, zoomlevel = None, sessionID = None):
	maxZoomLevel = get_max_zoomlevel(slideRef, sessionID)
	info = get_slide_info(slideRef, sessionID)
	if (zoomlevel is None or zoomlevel == maxZoomLevel):
		return (int(info["Width"]), int(info["Height"]))
	else:
		factor = 2 ** (zoomlevel - maxZoomLevel)
		return (int(info["Width"]) * factor, int(info["Height"]) * factor)

def get_number_of_tiles(slideRef, zoomlevel = None, sessionID = None):
	pixels = get_pixel_dimensions(slideRef, zoomlevel, sessionID)
	sz = get_tile_size(sessionID)
	return (int(ceil(pixels[0] / sz[0])), int(ceil(pixels[1] / sz[0])))
	
def get_physical_dimensions(slideRef, sessionID = None):
	ppmData = get_pixels_per_micrometer(slideRef, sessionID)
	pixelSz = get_pixel_dimensions(slideRef, sessionID)
	return (pixelSz[0] * ppmData[0], pixelSz[1] * ppmData[1])
			
def get_number_of_channels(slideRef, sessionID = None):
	info = get_slide_info(slideRef, sessionID)
	channels = info["TimeFrames"][0]["Layers"][0]["Channels"]
	return len(channels)

def is_fluorescent(slideRef, sessionID = None):
	"""Determine whether a slide is a fluorescent image or not"""
	return get_number_of_channels(slideRef, sessionID) > 1

def determine_magnification(slideRef, zoomlevel = None, exact = False, sessionID = None):
	ppm = get_pixels_per_micrometer(slideRef, zoomlevel, sessionID)[0]
	if (ppm > 0):
		if (exact == True):
			return round(40 / (ppm / 0.25))
		else:
			return round(40 / round(ppm / 0.25))
	else:
		return 0
	
def get_tile(slideRef, x = 0, y = 0, zoomlevel = None, sessionID = None):
	sessionID = _pma_session_id(sessionID)
	if (zoomlevel is None):
		zoomlevel = 0   # get_max_zoomlevel(slideRef, sessionID)
	url = (_pma_url(sessionID) + "tile"
		+ "?SessionID=" + _pma_q(sessionID)
		+ "&channels=" + _pma_q("0")
		+ "&timeframe=" + _pma_q("0")
		+ "&layer=" + _pma_q("0")
		+ "&pathOrUid=" + _pma_q(slideRef)
		+ "&x=" + _pma_q(x)
		+ "&y=" + _pma_q(y)
		+ "&z=" + _pma_q(zoomlevel)	)
	r = requests.get(url)
	img = Image.open(BytesIO(r.content))
	return img

def get_tiles(slideRef, fromX = 0, fromY = 0, toX = 0, toY = 0, zoomlevel = None, sessionID = None):
	sessionID = _pma_session_id(sessionID)
	if (zoomlevel is None):
		zoomlevel = 0   # get_max_zoomlevel(slideRef, sessionID)
	for x in range(fromX, toX):
		for y in range(fromY, toY):
			yield get_tile(slideRef, x, y, zoomlevel, sessionID)