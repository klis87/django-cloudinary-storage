from setuptools import setup

setup(
    name='django-cloudinary-storage',
    version='1.0',
    author='Konrad Lisiczynski',
    author_email='klisiczynski@gmail.com',
    packages=['cloudinary_storage'],
    install_requires=[
        'requests>=2.10.0',
        'cloudinary>=1.4.0'
    ],
    extras_require={
        'video': ['python-magic>=0.4.12']
    }
)
