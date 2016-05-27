from setuptools import setup, find_packages

setup(
    name='async_fsm',
    packages=find_packages(),
    install_requires=[
        'promise',
        'PyYAML',
    ],
    tests_require=[
        'tox',
        'eventlet',
        'pytest',
        'pytest-asyncio',
        'coverage',
    ],
)
