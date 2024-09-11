from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    description = f.read()

setup(
    name='dbscripts',
    version='0.1.35',
    author="KCatterall",
    license='MIT',
    url='https://github.com/Catterall/dbscripts',
    download_url='https://github.com/Catterall/dbscripts/releases',
    packages=find_packages(),
    install_requires=[
        'pyodbc>=5.1.0'
    ],
    description="A small Python package for handling 'database scripts', including analysis and dependency management.",
    long_description=description,
    long_description_content_type='text/markdown',
)