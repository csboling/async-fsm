from setuptools import setup, find_packages

setup(
    name='service-host',
    packages=find_packages(),
    install_requires=[
        'nameko',
        'gitpython',
	'promise',

        'egor',
    ],
    tests_require=['tox'],
)
