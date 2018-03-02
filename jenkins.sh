#!/bin/bash
python bootstrap.py -c jenkins.cfg -v 1.7.0

./bin/buildout -c jenkins.cfg
./bin/supervisorctl shutdown && true
./bin/supervisord
echo "Wait for solr to come up"
while ! nc -z localhost 9110; do sleep 1; done
echo "Solr server ready"
sleep 2
./bin/test --with-xunit --sphinx-doc --sphinx-doc-dir=./docs/source/test --webapp-chats --with-xcoverage --cover-package=restrepo --cover-erase --cover-branches restrepo -v
./bin/supervisorctl shutdown && true
rm docs/build/html/ -rf
rm docs/build/doctrees/ -rf
./bin/sphinxbuilder
sloccount --duplicates --wide --details restrepo|grep -v restrepo/tests/test_files/ > sloccount.sc
find . -name \*.py|egrep -v '^./tests/'|xargs ./bin/pyflakes  > pyflakes.log
./bin/pep8 --repeat restrepo --ignore=E126,E128,E501 > pep8.log
./bin/pylint -f parseable restrepo --ignore=magic.py --disable=C0111 --disable=E1101 --disable=C0301 --variable-rgx="[a-z_][a-z0-9_]{1,30}$" > pylint.log
./bin/clonedigger --cpd-output restrepo
