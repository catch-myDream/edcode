from setuptools import setup, find_packages

with open('README.md','r') as f:
    desc = f.read()

setup(
    name='edcode',
    version='1.1',

    py_modules=['app.edcode'],
    install_requires=[],
    entry_points={
        'console_scripts': [
            'edcode=app.edcode:main',
        ],
    },
    long_description=desc,
    long_description_content_type='text/markdown',
    
)
