import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="vassal",
    version="0.0.2",
    author="Shawn Shan",
    author_email="shawnshan1825@gmail.com",
    description="The automate terminal",
    long_description=long_description,
    url="https://github.com/Shawn-Shan/vassal",
    packages=setuptools.find_packages(),
    install_requires=[
        'scp>=0.13.0',
        'cryptography>=2.4.1',
        'paramiko>=2.4.2',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
