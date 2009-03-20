GUM (Group, User Manager)
-------------------------

GUM allows you to manage user accounts and groups stored in an LDAP server.
It provides a user-friendly web interface for managing those users and
groups. It also has a plug-in system to allow Python extensions to be
called when modifications are made to LDAP entries.

GUM is written in Python using the Grok web framework.

Installation
------------

GUM is intended to be installed using Buildout. It requires Python 2.6.

  $ python2.6 bootstrap/bootstrap.py
  $ ./bin/buildout
  
From here you can start a development LDAP server with:

  $ ./bin/slapd start
  
Then start the web server with:

  $ ./bin/zopectl start
  
This will start the server on port 8080.

More likely than not though, you want to install a version to use in
production. In this case, copy the 'buildout.cfg' file and name it
'production.cfg'. Then edit this file with production configuration,
and install it with:

  $ ./bin/buildout -c production.cfg
  
But the buildout config is still a bit murky at the moment, as well
as the post-installation experience -- if you are trying to install this
and get stuck, please contact the author by email.

Develop
-------

To develop GUM you should have an LDAP instance for developing with.
You must have OpenLDAP pre-installed (currently this works on Mac OS X,
will need tweaking for other OSes). You must start this instance before
running the app or functional tests:

  $ ./bin/slapd start

If you need to debug LDAP, it can be started in debug mode with:

  $ /usr/libexec/slapd -f ./parts/slapd/slapd.conf -d 255 \
    -h ldap://127.0.0.1:1700

Note that the functional tests expect the server to start on port 1700.
