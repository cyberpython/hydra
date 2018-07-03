import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hydra_framework",
    version="0.2.1",
    author="George Migdos",
    author_email="cyberpython@gmail.com",
    description="Python framework that provides the basic building blocks to implement data processing graphs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cyberpython/hydra",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    install_requires=['Flask']
)