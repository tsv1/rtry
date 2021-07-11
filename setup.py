from setuptools import find_packages, setup


def find_required():
    with open("requirements.txt") as f:
        return f.read().splitlines()


def find_dev_required():
    with open("requirements-dev.txt") as f:
        return f.read().splitlines()


setup(
    name="rtry",
    version="1.3.0",
    description="The easiest way to retry operations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Nikita Tsvetkov",
    author_email="nikitanovosibirsk@yandex.com",
    python_requires=">=3.5.0",
    url="https://github.com/nikitanovosibirsk/rtry",
    license="MIT",
    packages=find_packages(exclude=("tests",)),
    package_data={"rtry": ["py.typed"]},
    install_requires=find_required(),
    tests_require=find_dev_required(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Typing :: Typed",
    ],
)
