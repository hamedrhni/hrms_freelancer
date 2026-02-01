"""
HRMS Freelancer Extension
A Frappe Framework app for managing freelancers and contractors
"""
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

with open("README.md") as f:
    long_description = f.read()

setup(
    name="hrms_freelancer",
    version="1.0.0",
    description="Freelancer and Contractor Management Extension for Frappe HRMS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="HR Platform Team",
    author_email="support@hrplatform.example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Frappe",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Office/Business :: Human Resources",
    ],
)
