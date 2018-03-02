#!/bin/sh 

# PUT some basic info on scan
ab -c 1 -n 20 -v 1 -p scan_put_change_basic.txt -T 'application/x-www-form-urlencoded' localhost:5000/scans/1878

# MOVE a scan
# ab -c 10 -n 20 -v 0 -p scan_move.txt -T 'application/x-www-form-urlencoded' localhost:5000/scans/1878/move


