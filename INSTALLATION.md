# INSTALLATION

## INSTALL SOFTWARE PACKAGES

    sudo apt-get update
    sudo apt-get upgrade --show-upgraded
    sudo apt-get install git
    sudo apt-get install libjpeg-dev libjpeg62-dev zlib1g-dev libfreetype6-dev liblcms1-dev libevents-dev
    sudo apt-get install openjdk-8-jdk
    sudo apt-get install postgresql libpsql-dev postgresql-server-dev-all
    sudo apt-get install libxslt-dev  libxml2-dev
    sudo apt-get install python-dev
    sudo apt-get install python-setuptools
    sudo apt-get install netcat
    sudo apt-get install rabbitmq-server
    sudo apt-get install libevent-dev
    sudo apt-get install python-zmq
    sudo apt-get install libzmq-dev
    sudo apt-get install build-essential
    sudo easy_install fabric

## INSTALL PYTHON

The repository needs python version 2.7.
You can check the python version by doing:

    python --version

If it is not installed, do:

    wget http://www.python.org/ftp/python/2.7.3/Python-2.7.3.tar.bz2
    tar xf Python-2.7.3.tar.bz2
    cd Python-2.7.3
    ./configure
    make
    sudo make altinstall
    cd ..
    rm -rf Python-2.7.3


## CREATE THE DATABASE

create a user "dasa" that is not a superuser, cannot create databases, and cannot create roles:

    sudo su postgres -c "createuser dasa -SDR"

and create the main database, and the one used for testing (cf. the section CONFIGURATION below for details about these settings)

    sudo su postgres -c "createdb dasa_repository --owner=dasa"
    sudo su postgres -c "createdb restrepo_test --owner=dasa"


# INSTALL THE REPOSITORY SOFTWARE

First, clone the repository.

    git clone https://github.com/sejarah-nusantara/repository.git

The repository start a number of services. It uses a number of ports, defined in ports.cfg.
Before installing, you may want to check these settings.

    cd restrepo
    bin/buildout -c development.cfg

Now you should be able to start the services

# STARTING AND STOPPING THE SERVICES

After installation, the `bin`  directory contains a number of scripts that you can use to control the various services.

Probably the most useful is the process manager, `circus`, that you can use to start and stop individual services.

Start the circus daemon like this:

    bin/circusd circus.ini --daemon

Now you can use `circusctl` to check  status of the services:

    bin/circusctl


# CONFIGURE LOGGING

The default configuration (in restrepo.ini) writes its log files to /var/log/dasa/
We user that runs the process should have write access to this directory

> sudo /var/log/dasa
> sudo chown dasa: /var/log/dasa

# UPGRADING

get the latest version of the software

> git pull

and re-install the software

> fab install

# CONFIGURE YOUR WEB SERVER

The repository application is listening on port 5000. See "CONFIGURATION" if you need to change this.

Documentation consists of static HTML files in the directory repository/docs/build/html

A typical configuration for Apache is is this:


    <VirtualHost *:80>  
        ServerName repository.cortsfoundation.org:80  
        ServerAlias repository.cortsfoundation.org

        RewriteEngine On
        RewriteRule ^/(.*) http://localhost:5000/$1 [L,P]
        ProxyPreserveHost On

        # alert, emerg.  
        LogLevel warn  
        CustomLog /var/log/apache2/repository.cortsfoundation.org_access.log combined
        ErrorLog /var/log/apache2/repository.cortsfoundation.org_errors.log  
    </VirtualHost>



# CONFIGURATION

## CFG Files
Various system settings are defined in base.cfg.

If you change these settings, you need to re-generate the scripts, and restart the services.

You can either use the installation command:

> fab install

A quicker alternative to reload the new settings is this:

# TODO: supervisorctl HAS BECOME CIRCUS
> bin/supervisorctl shutdown
> bin/buildout -N -c production.cfg
> bin/supervisord


Here are some settings that you may need to change in the file "base.cfg":

*ports* are defined in the section [ports]. The value for "main" is where the application is listening

*ip-based authorization*: there is a list of authorized IP addresses in the section [settings].

*database connections*: are defined in the section [settings]

## Watermark

Some settings for the watermarker can be controlled via a web form that can be found on:

    http://url.of.repository/configuration

VERSIONS
---------------
This installation procedure was tested using the following configurations:

> lsb_release -d
Description:	Ubuntu 12.04.2 LTS
> dpkg -l | grep -e libjpeg62-dev -e zlib1g-dev -e libfreetype6-dev -e liblcms1-dev -e openjdk-6-jdk  -e postgresql  -e libpsql-dev -e postgresql-server-dev-all -e libxslt-dev -e  libxml2-dev -e python-dev -e python-setuptools -e " git " -e netcat
ii  git                                  1:1.7.9.5-1                      fast, scalable, distributed revision control system
ii  libfreetype6-dev                     2.4.8-1ubuntu2.1                 FreeType 2 font engine, development files
ii  libjpeg62-dev                        6b1-2ubuntu1                     Development files for the IJG JPEG library (version 6.2)
ii  liblcms1-dev                         1.19.dfsg-1ubuntu3               Litle CMS color management library development headers
ii  libxml2-dev                          2.7.8.dfsg-5.1ubuntu4.3          Development files for the GNOME XML library
ii  netcat                               1.10-39                          TCP/IP swiss army knife -- transitional package
ii  netcat-traditional                   1.10-39                          TCP/IP swiss army knife
ii  openjdk-6-jdk                        6b24-1.11.5-0ubuntu1~12.04.1     OpenJDK Development Kit (JDK)
ii  postgresql                           9.1+129ubuntu1                   object-relational SQL database (supported version)
ii  postgresql-9.1                       9.1.8-0ubuntu12.04               object-relational SQL database, version 9.1 server
ii  postgresql-client-9.1                9.1.8-0ubuntu12.04               front-end programs for PostgreSQL 9.1
ii  postgresql-client-common             129ubuntu1                       manager for multiple PostgreSQL client versions
ii  postgresql-common                    129ubuntu1                       PostgreSQL database-cluster manager
ii  python-dev                           2.7.3-0ubuntu2                   header files and a static library for Python (default)
ii  python-setuptools                    0.6.24-1ubuntu1                  Python Distutils Enhancements (setuptools compatibility)
ii  zlib1g-dev                           1:1.2.3.4.dfsg-3ubuntu4          compression library - development




> lsb_release -d
Description:	Ubuntu 11.10
> dpkg -l | grep -e libjpeg62-dev -e zlib1g-dev -e libfreetype6-dev -e liblcms1-dev -e openjdk-6-jdk  -e postgresql  -e libpsql-dev -e postgresql-server-dev-all -e libxslt-dev -e  libxml2-dev -e python-dev -e python-setuptools -e " git "
ii  git                                    1:1.7.5.4-1                                  fast, scalable, distributed revision control system
ii  libfreetype6-dev                       2.4.4-2ubuntu1.3                             FreeType 2 font engine, development files
ii  libjpeg62-dev                          6b1-1ubuntu2                                 Development files for the IJG JPEG library (version 6.2)
ii  liblcms1-dev                           1.19.dfsg-1ubuntu2                           Litle CMS color management library development headers
ii  libxml2-dev                            2.7.8.dfsg-4ubuntu0.5                        Development files for the GNOME XML library
ii  openjdk-6-jdk                          6b24-1.11.5-0ubuntu1~11.10.1                 OpenJDK Development Kit (JDK)
ii  netcat-openbsd                         1.89-4ubuntu1                                TCP/IP swiss army knife
ii  postgresql                             9.1+122ubuntu1                               object-relational SQL database (supported version)
ii  postgresql-8.4                         8.4.14-0ubuntu11.04                          object-relational SQL database, version 8.4 server
ii  postgresql-9.1                         9.1.7-0ubuntu11.10                           object-relational SQL database, version 9.1 server
ii  postgresql-client                      9.1+122ubuntu1                               front-end programs for PostgreSQL (supported version)
ii  postgresql-client-8.4                  8.4.14-0ubuntu11.04                          front-end programs for PostgreSQL 8.4
ii  postgresql-client-9.1                  9.1.7-0ubuntu11.10                           front-end programs for PostgreSQL 9.1
ii  postgresql-client-common               122ubuntu1                                   manager for multiple PostgreSQL client versions
ii  postgresql-common                      122ubuntu1                                   PostgreSQL database-cluster manager
ii  python-dev                             2.7.2-7ubuntu2                               header files and a static library for Python (default)
ii  python-setuptools                      0.6.16-1ubuntu0.1                            Python Distutils Enhancements (setuptools compatibility)
ii  zlib1g-dev                             1:1.2.3.4.dfsg-3ubuntu3                      compression library - development
