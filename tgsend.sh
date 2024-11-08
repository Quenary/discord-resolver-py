#!/bin/bash
MESSAGE="$1"
source secret
curl -s -X POST -H "Content-Type: application/json" -d "{ \"message\":\"$MESSAGE\" }" $NOTIFY_URL
