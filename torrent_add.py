import yaml
import transmissionrpc
import base64
import re
import argparse


class Settings:
	transmission = {'host':'localhost','port':'9091'}

	isPreservDownloadDir = True
	isPreservSkipedFiles = True
	isPreservTorrentState = True

	commentSearchPatterns =	[ 
		['.*',None] 
	]	 
	
settings = None;
args = None;
transmis = None;

def main():
	
	global settings;
	global args;

	if loadArgs(): return;
	if loadSettings(): return;
	
	initTransmissionConnection();

	curTorrent = None;

	if not args.id:
		curTorrent = addTorrentFile(args.filename);
		#check if already exists not implemented\
		curTorrent = transmis.get_torrents(curTorrent.id)[0];
	else:
		curTorrent = transmis.get_torrents(args.id)[0]

	if curTorrent == None:
		print "No torrent fund!"
		return

	#only adding torrent
	if args.add_only:
		return;

	searchPattern = ['.*',None]

	for curPattern in settings.commentSearchPatterns:
		if re.match(curPattern[0], curTorrent.comment):
			searchPattern = curPattern;
			break;

	print 'Using match: ',searchPattern

	
	res, curTorrentCommentPattern = checkPattern(searchPattern, curTorrent.comment);

	if not res:
		print 'No match'
		return

	torrents = transmis.get_torrents();

	oldTorrent =  None;

	for tor in torrents:
		res, pattern = checkPattern(searchPattern, tor.comment);
		if res and pattern == curTorrentCommentPattern and tor.id != curTorrent.id:
			print "OK Find old torrent"
			print tor.name
			oldTorrent = tor;
			break;
		else:
			print 'Skip torrent ', tor


	if oldTorrent:
		if settings.isPreservDownloadDir:
			curTorrent.downloadDir = oldTorrent.downloadDir;
		print 'remove old ', oldTorrent.id, '-', oldTorrent.name
		transmis.remove_torrent(oldTorrent.id)


def checkPattern(pattern, comment):

	if not pattern[1]:
		return False, None

	m = re.match(pattern[0], comment)
	
	if m: 
		return True, m.expand(pattern[1])

	return False, None


def addTorrentFile(filename):
	global transmis;

	file = open(filename, "rb")  
	data = file.read()  
	file.close()  
	byte_arr = base64.b64encode(data)

	return transmis.add_torrent(byte_arr);


def initTransmissionConnection():
	global transmis;

	transmis = transmissionrpc.Client(settings.transmission['host'],
		settings.transmission['port']);


def loadSettings():
	global settings;
	global args;

	settings = Settings();

	if args.config:
		stream = file(args.config, 'r')
		yaml_conf = yaml.load(stream);

		settings.transmission = yaml_conf['transmission']
		settings.isPreservDownloadDir = yaml_conf['options']['preservDownload']
		settings.isPreservSkipedFiles = yaml_conf['options']['preservFiles']
		settings.isPreservTorrentState = yaml_conf['options']['preservState']

		settings.commentSearchPatterns = yaml_conf['comment-regs']

		settings.commentSearchPatterns.append(['.*',None])

	
	if args:
		if args.preserv_download_dir:
			settings.isPreservDownloadDir = True

		if args.preserv_skiped_files:
			settings.isPreservSkipedFiles = True

		if args.preserv_state:
			settings.isPreservTorrentState = True

		if args.not_preserv_download_dir:
			settings.isPreservDownloadDir = False

		if args.not_preserv_skiped_files:
			settings.isPreservSkipedFiles = False

		if args.not_preserv_state:
			settings.isPreservTorrentState = False

	#print settings.commentSearchPatterns

	return 0


def loadArgs():
	global args;

	parser = argparse.ArgumentParser(description='Process some integers.')

	parser.add_argument('filename', nargs='?',
                     help='local path to torrent file')
	parser.add_argument('-i','--id',
                     help='id for torrent what already been added to transmission')
	parser.add_argument('-a','--add-only', action='store_true',
                     help='only add torrent, don\'t check is it update' )

	parser.add_argument('-d','--preserv-download-dir', action='store_true',
                     help='copy download dir from old torrent' )
	parser.add_argument('-s','--preserv-state', action='store_true',
                     help='set old torrent\'s state to new' )
	parser.add_argument('-f','--preserv-skiped-files', action='store_true',
                     help='mark same skiped files as old ones' )

	parser.add_argument('--not-preserv-download-dir', action='store_true',
                     help='don\'t copy download dir from old torrent' )
	parser.add_argument('--not-preserv-state', action='store_true',
                     help='don\'t set old torrent\'s state to new' )
	parser.add_argument('--not-preserv-skiped-files', action='store_true',
                     help='dont\'t mark same skiped files as old ones' )
	parser.add_argument('-c','--config',
                     help='config filename')

	args =  parser.parse_args()

	#print args

	if not args.id  and not args.filename:
		print 'No torrent specified'
		return 2

	if args.id and args.filename:
		print 'Warrning: multiply torrent idefication, will use transmission id!'

	return 0



if __name__ == '__main__':
	main();
	

