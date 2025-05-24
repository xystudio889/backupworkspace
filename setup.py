from setuptools import setup, find_packages

setup(
    name="backupworkspace",
    version="0.2.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[],
    python_requires=">=3.8",
    author="xystudio",
    author_email="173288240@qq.com",
    description="Quickly back up your workspace.",
    long_description=open("README-PYPI.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/xystudio889/backupworkspace",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "backup = backup:main",
        ]
    },
    extras_require={
        "dev": []
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords = ["config", "configure", "toml"]
)
