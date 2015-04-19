import sys
import torrent_parser_nnm
import logging
import datetime
import yaml
import sqlite3
import argparse
import shutil

db = None

transmission = None

defaultAction = None

transmissionSettings = None

parserSettings = None
parserActions = None
parsers = {}

args = None


def main():
	global args
	global logger

	print 'Torrent watcher'
	_loadArgs()
	_loadSettings()

	if args.status:
		printStatus()
		return

	if args.transmission_id:
		importFromTransmission(args.transmission_id)

	if args.import_url:
		importFromUrl(args.import_url)

	logger.debug('Start updating torrents')

	torrents = _sqlGetTorrents()

	for torrent in torrents:
		try:
			logger.debug("Check update for %s", torrent['name'])
			torrent['laststatus'] = "Prepare to update"
			logger.debug("Get parser %s", torrent['parser'])
			parser = _getParser(torrent['parser'])
			parOpt = torrent[torrent['parser']]

			if parser.CheckTorrentUpdate(parOpt):
				logger.debug("Update for %s", torrent['name'])
				torrent['laststatus'] = "Pending update"

				_doAction(parserAction[torrent['parser']], parser, torent)

				##Update sucseed
				_sqlUpdateTorrentData(torrent)
			else:
				logger.debug("No update for %s", torrent['name'])
				torrent['laststatus'] = "Up to date"
		except:
			logger.debug(str(sys.exc_info()[0]))
			torrent['laststatus'] = "Error while update"
		finally:
			logger.debug("updating torrent status")
			_sqlUpdateTorrentInfo(torrent)



def printStatus():
	global db

	print "Status report:"

	cursor = db.cursor()

	# cursor.execute('''insert into torrents(id,name,laststatus)
	# 	VALUES(?,?,?)''',(1,'Test torrent 1', None))
	# db.commit()

	cursor.execute(''' select * from [torrents]''')
	data = cursor.fetchall()

	if len(data) <= 0:
		print "No torrents"
		return

	for row in data:
		print u"{0}\t{1}\t{2}".format(row[0],row[1],row[2]).encode('UTF-8')

	return


def importFromTransmission(tid):
	global logger

	if not transmission:
		raise Exception("transmission is not configured")

	logger.debug("Import watch torrents from transmission by %s", tid)


def importFromUrl(url):
	global logger
	global parsers
	global parserSettings

	if len(parserSettings.keys()) <= 0:
		raise Exception("no single parser is not configured")

	logger.debug("Import watch torrents from %s", url)

	curParser = None
	parserKey = None

	for parser in parserSettings.keys():
		logger.debug("Trying parser %s", parser)
		info, error = _checkUrl(parser,url)
		if info:
			curParser = _getParser(parser)
			parserKey = parser
			break;
		logger.debug("Parser %s error: %s",parser, error)

	if not curParser:
		raise Exception("Url don't match any parser")

	torrent = {}

	torrent['id'] = -1
	torrent['name'] = curParser.GetTorrentName(info)
	torrent['parser'] = curParser.GetKey()
	torrent[curParser.GetKey()] = info

	_sqlAppendTorrent(torrent)

def _checkUrl(parser, url):

	curp = _getParser(parser);
	try:
		info = curp.GetTorrentInfo(url)
		return info, None
	except:
		return None, sys.exc_info()[0]


def _loadSettings():
	global args
	global logger
	global parserSettings
	global defaultAction

	if not args.config:
		return;

	stream = file(args.config, 'r')
	yaml_conf = yaml.load(stream);

	general = None

	if 'general' in yaml_conf:
		general = yaml_conf['general']

	_configLog(general)
	_configSqlite(general)

	defaultAction = _getAction(general['action'])

	#_configTransmission(yaml_conf['transmission'])

	#defaultAction = yaml_conf['general']['action']

	parserSettings = {}
	for prs in yaml_conf.keys():
		if prs != 'general' and prs != 'transmission':
			parserSettings[prs] = yaml_conf[prs]

def _configSqlite(conf):
	global db
	global logger

	dbname = 'watch.sqlite'

	if 'sqlite' in conf.keys():
		dbname = conf['sqlite']

	logger.debug("Open sqlite db %s", dbname)
	db = sqlite3.connect(dbname)

	cursor = db.cursor()
	cursor.execute(''' create table if not exists torrents(
		id integer primary key,
		name TEXT,
		laststatus TEXT,
		parser TEXT) ''')

	cursor.execute(''' create table if not exists torrents_data(
		id integer primary key,
		torrentId integer,
		key TEXT,
		name TEXT,
		value TEXT,
		type TEXT) ''')

def _getAction(param):

	res = {}

	if 'save' in param.keys():
		res['save'] = _skipDir(param['save'])

	if 'runscript' in param.keys() and 'save' in param.keys():
		res['runscript'] = param['runscript']

	if 'transmission' in param.keys():
		res['transmission'] = param['transmission']

def _doAction(action, parser, torrent):

	if 'save' in action.keys():
		tfile, filename = parser.GetTorrentFile(torrent[parser.GetKey()],
			torrent['name'] )
		try:
			dr = action['save']

			outFile = open(dr+'\\'+filename,'wb')
			try:
				shutil.copyfileobj(tfile, outFile)
			finally:
				outFile.close()
		finally:
			if tfile: tfile.close()
	else:
		logger.info('Not implemnt action')


def _sqlAppendTorrent(torrent):
	cursor = db.cursor()
	logger.debug("Add torrent %s to sqlite db", torrent['name'])
	try:
		cursor.execute('''insert into torrents(name,laststatus, parser) VALUES
			(?,?,?)''', (torrent['name'].decode('UTF-8'), u"Added",
				torrent['parser'].decode('UTF-8')))

		tid = cursor.lastrowid

		logger.debug("Added with id: %s", tid)

		for key in torrent.keys():
			logger.debug("Saving data %s", key)
			print torrent[key]
			if (key != 'name' and key !='id' and key !='laststatus' and key !='parser'):
				for name in torrent[key].keys():
					data, tp = _sqlSetValue(torrent[key][name])
					cursor.execute('''insert into torrents_data(torrentId, key, name, value, type)
					values (?,?,?,?,?)''',(tid, key.decode('UTF-8'), name.decode('UTF-8'),
			 		data.decode('UTF-8'), tp
			 		))

		db.commit()

	except:
		db.rollback()
		raise

def _sqlUpdateTorrentInfo(torrent):
	cursor = db.cursor()
	logger.debug("Update torrent %s to sqlite db", torrent['name'])
	tid = torrent['id'];
	try:
		cursor.execute('''update torrents set name = ?,laststatus =?, parser=? where id = ?''',
		 (torrent['name'], torrent['laststatus'], torrent['parser'], tid)
				);

		db.commit()
	except:
		db.rollback()
		raise

def _sqlUpdateTorrentData(torrent):

	cursor = db.cursor()
	logger.debug("Update torrent data %s to sqlite db", torrent['name'])
	tid = torrent['id']

	try:
		for key in torrent.keys():
			logger.debug("Updating Saving data %s", key)
			print torrent[key]
			if (key != 'name' and key !='id' and key !='laststatus' and key !='parser'):
				for name in torrent[key].keys():
					data, tp = _sqlSetValue(torrent[key][name])
					cursor.execute('''update torrents_data set value=?, type=?
					 where  torrentId = ? and key = ? and name =?''',
					(data, tp, tid, key, name
			 		))

		db.commit()

	except:
		db.rollback()
		raise


def _sqlGetTorrents():
	cursor = db.cursor()
	logger.debug("Getting torrents from sqlite db")

	cursor.execute('''select id, name, laststatus, parser from torrents''')

	data = cursor.fetchall()

	torrents = []

	for row in data:
		torrent = {}
		torrent['id'] = row[0]
		torrent['name'] = row[1]
		torrent['laststatus']=row[2]
		torrent['parser']=row[3]

		tid = torrent['id']

		logger.debug("Get torent id: %s", tid)

		cursor.execute(''' select distinct key from torrents_data 
			where torrentId = ?''', str(tid))

		keys = cursor.fetchall()

		print keys

		for key in keys:
			data = {}

			cursor.execute('''select name, value, type from torrents_data
				where torrentId = ? and key = ?''', (str(tid), str(key[0])))

			dt = cursor.fetchall()

			for dtRow in dt:
				print dtRow
				data[dtRow[0]] = _sqlGetValue(dtRow[1], dtRow[2]) 

			torrent[key[0]] = data

		torrents.append(torrent)

	return torrents

def _sqlGetValue(data, dttype):

	if (dttype=='int'):
		return int(data)

	if (dttype=='float'):
		return float(data)

	if (dttype=='datetime'):
		return datetime.datetime.strptime(data, '%y %m %d %H:%M:%S')

	return str(data.encode('UTF-8'))

def _sqlSetValue(data):

	print data 
	if type(data) is int:
		return str(data), "int"
	if type(data) is float:
		return str(data), 'float'
	if type(data) is datetime.datetime:
		return datetime.datetime.strftime(data,'%y %m %d %H:%M:%S'), 'datetime'

	print "type string"
	return str(data), 'string'

def _skipDir(dirname):
	if dirname[-1:] == '\\':
		return dirname[:-1]
	return dirname

def _configLog(conf):
	global logger
	#logging.basicConfig()
	logger = logging.getLogger(__name__)

	if conf:
		if 'loglevel' in conf.keys():
			if conf['loglevel'] == 'debug':
				logging.basicConfig(level=logging.DEBUG)

	logger = logging.getLogger(__name__)


def _loadArgs():
	global args;

	parser = argparse.ArgumentParser(description='Watch torrents')

	parser.add_argument('-c','--config',
                     help='config file')
	parser.add_argument('-p','--pid', 
                     help='pid file' )

	parser.add_argument('--status', action='store_true',
                     help='print status for all watched torrents' )
	parser.add_argument('--import-from-transmission', dest='transmission_id',
                     help='import torrents to watch from transmission by id or hash (-1 - all)' )
	parser.add_argument('-i','--import-from-url', dest='import_url',
                     help='imprt torrents from forum topic page' )
	parser.add_argument('--proxy', dest='proxy', help='proxy for web connections')
	

	args =  parser.parse_args()



def _getParser(name):
	global parsers
	global parserActions
	global parserSettings
	global defaultAction

	if name not in parsers.keys():
		if name == 'nnm':
			try:
				p = torrent_parser_nnm.NnmParser()
				p.OpenSession("vfrc2","EevCufcy", proxies={'http':args.proxy})
				
				if 'action' in parserSettings.keys():
					parserAction[name] = _getAction(parserSettings['action'])
				else:
					parserAction[name] = defaultAction;

			except:
				logger.error('Error init parser %s', name)
				logger.error(sys.exc_info()[0])
				p = None

			parsers[name] = p
		else:
			raise Exception('No parser for \'%s\\',name)
	
	if parsers[name]:
		return parsers[name]



if __name__ == '__main__':
	main();

