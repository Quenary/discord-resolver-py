#!/bin/bash
BGP_HOST="192.168.0.14"
cd /root/discord-resolver-py
./tgsend.sh "Starting discord domains update."
source venv/bin/activate
python main.py
deactivate
scp dest/cidr.txt root@$BGP_HOST:/root/discord-resolver-cidr.txt
ssh root@$BGP_HOST /usr/local/bin/bird-blocked
sleep 10
./tgsend.sh "Completed discord domains update, BGP restarted."
