import os
from setuptools import setup

install_requires = ["requests"]

base_dir = os.path.dirname(os.path.abspath(__file__))

setup(
    name = "mmupload",
    version = "0.0.2.dev",
    description = "flask-based (web-)file uploader & manager",
    #long_description="\n\n".join([
    #    open(os.path.join(base_dir, "README.md"), "r").read(),
    #    open(os.path.join(base_dir, "CHANGELOG.md"), "r").read()
    #]),
    url = "https://github.com/daringer/mmupload",
    author = "Markus 'Daringer' Meissner",
    author_email = "coder@safemailbox.de",
    packages = ["mmupload"],
    zip_safe = False,
)
