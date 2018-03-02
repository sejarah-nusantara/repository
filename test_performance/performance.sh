#!/bin/sh
ab -c 10 -n 40 -v 1 -p repo_post.txt -T 'application/x-www-form-urlencoded' 85.17.202.182:9900/scans/4363


