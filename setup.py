import os
from setuptools import setup
from chargeable import __version__

setup(
    name="django-chargeable",
    version=__version__,
    author="Anton Shutik",
    author_email="anton.shutik@itechart-group.com",
    description="Simple wrapper for django chargeable models",
    license="MIT",
    keywords="django stripe charge",
    url="https://github.com/Anton-Shutik/django-chargeable.git",
    packages=['chargeable'],
    classifiers=[
        "Topic :: Utilities",
    ],
    install_requires=[
        'Django>=1.0',
        'stripe'
    ],
    include_package_data=True,
)
