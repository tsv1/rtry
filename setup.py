from setuptools import find_packages, setup

setup(
    name="rtry",
    version="1.1.2",
    description="The easiest way to retry operations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Nikita Tsvetkov",
    author_email="nikitanovosibirsk@yandex.com",
    python_requires=">=3.5.0",
    url="https://github.com/nikitanovosibirsk/rtry",
    license="MIT",
    packages=find_packages(exclude=("tests",)),
    install_requires=[],
    tests_require=[
        "codecov==2.0.15",
        "coverage==4.5.3",
        "flake8==3.7.7",
        "isort==4.3.17",
        "mypy==0.670",
    ],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
    ],
)
