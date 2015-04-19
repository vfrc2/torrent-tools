torrent-add.py [a] | [udsf] <file.torrent>| -i <id>
	<file> - path to torrent file
	-i - id in current transmission session
	-a --add-only         - add torrent only if it's not in transmmision
	-u --update (default) - add or update torrent in tramsmission check hash and comment for torrent file and torrent in transmission if where is torrent with same comment in transmission then delete old and add new one else add new
	
	Modifiers for update:
	-d - preserve download dir from transmission
	-s - preserve state
	-f - preserve skiped files

requer python modules: yaml, transmissionrpc

config.yaml:

#Options for connect transmission	
taransmission:
  host: localhost
  port: 1234

preservDownload:yes
preservState:yes
preservFiles:yes

#Reg exp for parse comments
#exit on first match on input torrent comment, non pattern match - file is uniq
#when check all torrents in transmission with same pattern

comment-regs:
#[<regexp>,<pattern>] <pattern> for 
- [.*, /0] 


torrent-updater

hash torrent-name thread-url 
	
		
