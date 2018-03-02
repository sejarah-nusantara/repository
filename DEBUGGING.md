TESTING WITH CURL
-----------------

# operations on scans
curl http://localhost:5000/scans -X POST -d status=1
curl -X POST --form "file=@src/restrepo/restrepo/tests/test_files/purple.jpg" -F "user=jelle" -F "archive_id=1" -F "archiveFile=TEST" http://localhost:5000/scans
curl -X PUT -F "archiveFile=TEST2" -F "user=jelle" http://127.0.0.1:5000/scans/276015
curl -X POST -F "originalFolioNumber=3141" https://repository.cortsfoundation.org/scans/2890 --user admin:password

curl -X DELETE -F "user=jelle" http://localhost:5000/scans/276015

# add an archive
curl -X POST -F "archive=RG1" -F "institution=GH-PRAAD" http://127.0.0.1:5000/lists/archives
curl -X DELETE  http://127.0.0.1:5000/lists/archives/12

curl -X POST --form "file=@src/restrepo/restrepo/tests/test_files/short_ead.xml" http://127.0.0.1:5000/ead
curl -X DELETE http://127.0.0.1:5000/ead/short_ead.xml

# publish an archive file

curl -X PUT -F "status=2" https://repository-dasa.anri.go.id/archivefiles/1/853
curl -X PUT -F "status=2" https://repository.cortsfoundation.org/archivefiles/1/1196


# publish locally

curl -X PUT -F "status=1" http://127.0.0.1:5000/archivefiles/1/2458
curl -X PUT -F "status=2" http://127.0.0.1:5000/archivefiles/1/2458


# simulate an error

curl -X POST -F "wrongparameter=RG1" http://127.0.0.1:5000/lists/archives


# CHECK IF UPDATING OF THE PAGEBROWSER WORKS

NB: ONLY ARCHIVEFILES THAT OCCUR IN EAD FILES ARE PUBLISHED IN THE PAGEBROWSER
    [so the test archivefile does not work - this bit me several times]

* do some publish/unpublish action in the scanstore at
   http://scanstore.dasa.anri.go.id/

* check the pagebrowser log, which should log all requests for updates:
  tail -f /home/dasa/site/var/log/pagebrowser.log

* if there is no change in the pagebrowser, check the celery queue
    http://repository.dasa.anri.go.id/flower/tasks?limit=100

* if the request did not arrive there, check the celery error log
   less /home/dasa/repository/var/log/celeryd_stderr.log

# reset amqp rabbitmq queues:

dasa@sejarah-nusantara:~/repository (master)$ bin/celery amqp exchange.delete celeryresults
dasa@sejarah-nusantara:~/repository (master)$ bin/celery amqp exchange.delete celery

# rabbitmq management console

http://localhost:15672/#/
