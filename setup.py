from setuptools import setup, find_packages
import os

version = '0.8.3dev'

setup(name='gum',
      version=version,
      description="GUM is a web application for managing users and groups stored in an LDAP server.",
      long_description=(open(os.path.join('README.txt')).read() +
                        '\n\n' +
                        open(os.path.join('HISTORY.txt')).read()),
      classifiers=[
      "Programming Language :: Python",
      "Development Status :: 4 - Beta",
      "Framework :: Zope3",
      "Intended Audience :: System Administrators",
      "License :: OSI Approved :: Zope Public License",
      "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
      ],
      keywords="",
      author="Kevin Teague",
      author_email="Kevin Teague <kteague@bcgsc.ca>",
      url="http://www.bcgsc.ca/platform/bioinfo/software/gum",
      license="ZPL",
      package_dir={'': 'src'},
      packages=find_packages('src'),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
        'grok',
        'ldappas',
        'ldapadapter',
        'hurry.query',
        'z3c.testsetup',
        'grokui.admin',
        'grokcore.startup',
        'bud.nospam',
        # packages for migration to Grok 1.2
        'zope.app.session',
        'zope.app.catalog',
        'zope.app.intid',
        'zope.app.keyreference',
        'zope.app.securitypolicy',
      ],
      entry_points="""
      [console_scripts]
      gum-debug = grokcore.startup:interactive_debug_prompt
      gum-ctl = grokcore.startup:zdaemon_controller

      [paste.app_factory]
      main = grokcore.startup:application_factory
      debug = grokcore.startup:debug_application_factory
      """,
)
