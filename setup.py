from setuptools import setup

description = ('Django package that provides Cloudinary storages for both media and static files '
               'as well as management commands for removing unnecessary files.')

with open('README.md') as f:
    long_description = f.read()

setup(
    name='django-cloudinary-storage',
    version='0.1',
    author='Konrad Lisiczynski',
    author_email='klisiczynski@gmail.com',
    description=description,
    long_description=long_description,
    licence='MIT',
    url='https://github.com/klis87/django-cloudinary-storage#how-to-run-tests',
    keywords='django cloudinary storage',
    packages=['cloudinary_storage'],
    include_package_data=True,
    install_requires=[
        'requests>=2.10.0',
        'cloudinary>=1.4.0'
    ],
    extras_require={
        'video': ['python-magic>=0.4.12']
    }
)
