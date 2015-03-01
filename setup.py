from setuptools import setup, find_packages

try:
    long_description = open("README.rst").read()
except IOError:
    long_description = ""

setup(
    name='django-squirrel',
    version='0.1',
    url='https://github.com/timsavage/django-squirrel',
    license='LICENSE',
    author='Tim Savage',
    author_email='tim@savage.company',
    description='Extra caching tools for Django',
    long_description=long_description,
    packages=find_packages(),
    install_requires=['six', 'django>=1.5'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
