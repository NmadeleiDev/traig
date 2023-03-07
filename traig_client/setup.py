import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="traig_client",
    version="0.1",
    author="Gregory Potemkin",
    author_email="potemkin3940@gmail.com",
    description="Small client for Traig",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NmadeleiDev/traig",
    project_urls={},
    packages=[
        "traig_client",
    ],
    install_requires=["requests"],
)
