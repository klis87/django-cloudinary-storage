from setuptools import setup

description = ('Django package that provides Cloudinary storages for both media and static files '
               'as well as management commands for removing unnecessary files.')

long_description = ('Django Cloudinary Storage is a Django package that facilitates integration with Cloudinary '
                    'by implementing Django Storage API. With several lines of configuration, you can start using '
                    'Cloudinary for both media and static files. Also, it provides management commands for removing '
                    'unnecessary files, so any cleanup will be a breeze. It uses pycloudinary package under the hood.')

setup(
    name='django-cloudinary-storage',
    version='0.2.0',
    author='Konrad Lisiczynski',
    author_email='klisiczynski@gmail.com',
    description=description,
    long_description=long_description,
    license='MIT',
    url='https://github.com/klis87/django-cloudinary-storage',
    keywords='django cloudinary storage',
    packages=[
        'cloudinary_storage',
        'cloudinary_storage.templatetags',
        'cloudinary_storage.management',
        'cloudinary_storage.management.commands'],
    include_package_data=True,
    install_requires=[
        'requests>=2.10.0',
        'cloudinary>=1.4.0'
    ],
    extras_require={
        'video': ['python-magic>=0.4.12']
    },
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
