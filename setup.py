from setuptools import setup


requires = [
    'python-daemon',
    'pyzmq',
]

setup(name='TerminalTimer',
      version='0.0.1',
      packages=['terminaltimer'],
      description='Add alarms from terminal to be monitored by a daemon.',
      author='jonatan',
      author_email='j6544436085@gmail.com',
      install_requires=requires,
      entry_points={
          'console_scripts': [
              'terminaltimer = terminaltimer.client:main'
          ]
      },
      python_requires='>=3.6',
      )
