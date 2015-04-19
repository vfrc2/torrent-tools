
# -*- coding: utf-8 -*-

import sys
import requests
import re
import datetime
import base64
import logging
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

url_root = r'http://nnm-club.me/forum/'
url_index = r'http://nnm-club.me/forum/index.php'
url_login = r'http://nnm-club.me/forum/login.php'
url_torrent= r'http://nnm-club.me/forum/viewtopic.php?t='
url_regexp=r'http://nnm-club.me/forum/viewtopic.php\?(p|t)=\d*'

class NnmParser:

	_session = None #current nnm-club session 
	_proxies = {}

	def GetName(this):
		return "NNM-Club Parser"

	def GetKey(this):
		return "nnm"

	def GetTorrentName(this,info):
		if 'title' in info.keys():
			return info['title']
		else:
			return 'Torrent '+info['plink']

	def OpenSession(this, user, passw, proxies=''):

		logger.debug('Opening session for user %s', user)

		this._proxies = proxies

		this._session = requests.Session()

		payload = {
			"username":user,
			"password":passw,
			"login": "%C2%F5%EE%E4"
		}

		#print url_login

		logger.debug('Post payload to %s', url_login)
		res = this._session.post(url_login, payload, proxies = this._proxies)

		this.CheckSession()

	def CheckSession(this):

		logger.debug('Check session for user')

		res = this._session.get(url_index, proxies = this._proxies)

		#print res.encoding 

		upage = res.text.encode('utf8')

		m = re.search(r'class=\"mainmenu\">Выход \[\s(.*)\s\]</a>', upage);

		if not m:
			raise Exception("Error login into account")

		return True;

	def CheckTorrentUpdate(this, torrentInfo, force=False):

		logger.debug('Check update for torrent')

		link = ''

		if 'plink' in torrentInfo.keys():
			logger.warn('No plink in info')
			link = torrentInfo['plink']

		if 'tlink' in torrentInfo.keys():
			logger.warn('No tlink in info')
			link = torrentInfo['tlink']

		if not link:
			logger.error('no link for topick or torrent')
			raise Exception('No id fro torrent can\'t get info')

		logger.info('Check for torrent. url: %s', link)

		torrentPage = this._parseTorrentPage(link)

		logger.debug('Compare dates %s < %s', torrentInfo['date'],
			torrentPage['date'])
		logger.debug('Force update is %s',force)

		if torrentInfo['date'] < torrentPage['date'] or force:
			logger.info('Upadating torrent')
			this._updateTorrent(torrentPage,torrentInfo)
			logger.debug(torrentInfo)
			return True


		return False;

	def GetTorrentFile(this, torrentInfo, tempfilename):
		global session;

		logger.debug('Geting torrent file')

		if 'dlink' in torrentInfo.keys():
			logger.warning('No dlink. Updating info')
			this.CheckTorrentUpdate(torrentInfo, True)

		logger.debug('Download torrent file from %s', torrentInfo['dlink'])

		res = this._session.get(torrentInfo['dlink'], proxies = this._proxies , stream=True)

		logger.debug('Headers: %s',res.headers)

		if 'content-type' in res.headers.keys() and res.headers['content-type'] == 'application/x-bittorrent':

			filename = tempfilename
			if 'content-disposition' in res.headers.keys():
				m = re.search(ur'filename="(.*)"',
					res.headers['content-disposition']) 
				print m.groups()
				if m:
					filename = m.group(1)

			return res.raw, filename

		raise Exception("No torrent file found")

		#return base64.b64encode(res.raw).encode('ascii');

	def GetTorrentInfo(this, url):

		logger.debug('Try get torrent info from url %s', url)

		match = re.match(url_regexp, url)

		if not match:
			raise Exception("Wrong format for NNM-Club url!" + url)

		return  this._parseTorrentPage(url)


	def _parseTorrentPage(this, link):
		logger.debug('Parsing page %s',link)

		if not this._session: 
			logger.warn('Session is not open. Opening...')
			OpenSession()

		res = this._session.get(link, proxies = this._proxies)

		upage = res.text.encode('utf8')

		torrentPage = {}

		###################
		logger.debug('get page title ')
		match = re.search(
			r'<title>(.*)</title>', upage)

		if not match:
			logger.warn('Error get page title')
		else:
			torrentPage['title'] = match.group(1)
			logger.debug(torrentPage['title'])


		###################
		logger.debug('get page universal link')
		match = re.search(
			r'<a\sclass="maintitle"\shref="(.*)"', upage)

		if not match:
			logger.warn('Error get torrent universal link')
		else:
			torrentPage['tlink'] = url_root+match.group(1)
			logger.debug(torrentPage['tlink'])

		##################
		logger.debug('get page post link')
		match = re.search(
			r'<a\sspan\sclass="gensmall"\shref="(viewtopic\.php\?p=\d*)'
			, upage)

		if not match:
			logger.warn("Error get torrent post link")
		else:
			torrentPage['plink'] = url_root+match.group(1)
			logger.debug(torrentPage['plink'])

		if not torrentPage['plink'] and not torrentPage['tlink']:
			raise Exception("Can't find indentity links  while parsing")

		###################
		logger.debug('get page torrent date')
		match = re.search(
			r'<td\sclass=\"genmed\">&nbsp;(\d{2}.*\d{4}\s\d{2}:\d{2}:\d{2})</td>',
			upage);

		if not match:
			raise Exception("Error get torrent date")

		torrentPage['date'] = this._parseDate(
			match.group(1).decode('UTF-8')) #date_object

		logger.debug(torrentPage['date'])

		####################
		logger.debug('get torrent download link')
		match = re.search(
			r'(download\.php\?id=\d{6,8})',
			upage);

		if not match:
			raise Exception("Error get torrent download link")

		torrentPage['dlink'] = url_root+match.group(1)

		logger.debug(torrentPage['dlink'])

		return torrentPage

	def	_updateTorrent(this, p, t):
		t['date'] = p['date']
		t['dlink'] = p['dlink']
		t['tlink'] = p['tlink']
		t['plink'] = p['plink']
		t['title'] = p['title']



	def _parseDate(this, strDate):
		match = re.match(
			u'(\d{2})\s(.{3})\s(\d{4})\s(\d{2}):(\d{2}):(\d{2})',
			strDate, re.UNICODE);

		if not match:
			raise Exception('Bad date string')
		
		day = int(match.group(1))

		monthDict = {
			u'Янв':1,
			u'Фев':2,
			u'Мар':3,
			u'Апр':4,
			u'Май':5,
			u'Июн':6,
			u'Июл':7,
			u'Авг':8,
			u'Сен':9,
			u'Окт':10,
			u'Ноя':11,
			u'Дек':12
		}

		month = monthDict[match.group(2)]
		year = int(match.group(3))
		hour = int(match.group(4))
		minut = int(match.group(5))
		sec = int(match.group(6))

		date = datetime.datetime(year, month, day,hour,minut,sec)

		#rint date
		#datetime(year, month, day[, hour[, minute[, second[, microsecond[, tzinfo]]]]])
		return date

