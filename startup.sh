#!/bin/sh
# git clone $REPO_URL /usr/share/nginx/html
if [ -n "$GITHUB_HOOK_SECRET" ]; then 
    sed -i "s/MY_SECRET/$GITHUB_HOOK_SECRET/" /root/hooks.json
fi
/etc/init.d/cron start
nginx
webhook -hooks /root/hooks.json -verbose

