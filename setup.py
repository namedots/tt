from setuptools import setup


requires = [
    'pyzmq',
]

setup(name='TerminalTimer',
      version='0.0.1',
      description='Timer/alarm daemon with a command for interaction.',
      author='jonatan',
      author_email='j6544436085@gmail.com',
      install_requires=requires,
      entry_points={
          'console_scripts': [
              'terminaltimer = terminaltimer.commandline:main'
          ]
      }
      )
