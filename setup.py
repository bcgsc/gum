from setuptools import setup, find_packages

version = '0.8.1 dev'

setup(name='gum',
      version=version,
      description="",
      long_description="",
      classifiers=[],
      keywords="",
      author="",
      author_email="",
      url="",
      license="",
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
