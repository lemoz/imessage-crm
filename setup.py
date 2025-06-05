#!/usr/bin/env python3
"""Setup script for iMessage CRM."""

from setuptools import setup, find_packages
import pathlib

# Get the long description from the README file
here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="imessage-crm",
    version="0.1.0",
    description="A lightweight CRM system for macOS iMessage conversations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/imessage-crm",
    author="iMessage CRM Contributors",
    author_email="your-email@example.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="imessage, crm, macos, messages, contacts, automation",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "py-applescript>=1.0.0",
        "apscheduler>=3.10.1",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "openai>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "imessage-crm=imessage_crm.main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/imessage-crm/issues",
        "Source": "https://github.com/yourusername/imessage-crm",
        "Documentation": "https://github.com/yourusername/imessage-crm#readme",
    },
    platforms=["macOS"],
)