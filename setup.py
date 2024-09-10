from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    description = f.read()

setup(
    name='dbscripts',
    version='0.1.1',
    author="KCatterall",
    license='MIT',
    url='https://github.com/Catterall/dbscripts',
    download_url='https://github.com/Catterall/dbscripts/releases',
    packages=find_packages(),
    install_requires=[
        'pyodbc>=5.1.0'
    ],
    description="A small Python package to quickly run database object scripts against a database without dependency issues.",
    long_description=description,
    long_description_content_type='text/markdown',
)