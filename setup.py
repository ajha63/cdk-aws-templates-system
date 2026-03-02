"""Setup script for CDK AWS Templates System."""

from setuptools import setup, find_packages

setup(
    name="cdk-aws-templates",
    version="1.0.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "pyyaml>=6.0",
        "jsonschema>=4.17.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "hypothesis>=6.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    python_requires=">=3.8",
)
