from setuptools import setup, find_packages

MAJOR_VERSION = 0
MINOR_VERSION = 1
MICRO_VERSION = 0


__version__ = "{}.{}.{}".format(MAJOR_VERSION, MINOR_VERSION, MICRO_VERSION)


setup(
    name="optimizer",
    version=__version__,
    description="",
    author="Bhargava Ram Kanda",
    author_email="bhargavkanda@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    license="",
    install_requires=[
        "pandas",
        "numpy",
	    "sympy"
    ],
)

