from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="Franci Gjeci",
    version='0.0.1',
    description='A package containing the MQTT paho based python clients. In addition there is a docker '
                'implementation of these clients, by using an available docker image, which runs python',
    author='Franci Gjeci',
    author_email="franci.gjeci@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
)