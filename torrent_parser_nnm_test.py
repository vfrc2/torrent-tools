import torrent_parser_nnm
import datetime
import logging
import shutil
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print "Test for NNM-Club parser"

logger.debug('Create parser')

parser = torrent_parser_nnm.NnmParser()

parser.OpenSession("vfrc2","EevCufcy", proxies={'http':'http://vfrc2.paata.ru:9123'})
#parser.OpenSession("vfrc2","EevCufcy")

logger.debug('Create parser')
res = parser.GetTorrentInfo('http://nnm-club.me/forum/viewtopic.php?t=887913')

if not res:
	logger.debug('Check unsucseed')
	print error
else:
	logger.debug('Check sucseed')



torrentInfo = {
	'tlink':'http://nnm-club.me/forum/viewtopic.php?t=887913',
	'date':datetime.datetime(1989,5,12)
}

logger.debug('Create torrentInfo')
logger.debug(torrentInfo)



logger.debug('Checking for update')
if parser.CheckTorrentUpdate(torrentInfo):
	logger.debug('Find update. Getting torrent file')

	tfile = None
	try:
		tfile, filename = parser.GetTorrentFile(torrentInfo, 'tor-file.torrent')
		
		logger.debug('Download %s', filename)

		outFile = open(filename,'wb')
		try:
			shutil.copyfileobj(tfile, outFile)
		finally:
			outFile.close()
	finally:
		if tfile: tfile.close()

else:
	logger.debug('No update')