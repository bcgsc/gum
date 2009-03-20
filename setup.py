from setuptools import setup, find_packages
import os

version = '0.8.2 dev'

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
        'bud.nospam',
        #'reportlab', grr! this is not installing ATM!
      ],
      entry_points="""
      """,
)
