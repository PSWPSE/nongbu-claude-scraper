"""
XTweet 패키지 설정
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="xtweet",
    version="1.0.0",
    author="XTweet Team",
    author_email="team@xtweet.com",
    description="웹 스크래핑 기반 자동 콘텐츠 생성 및 슬랙 연동 시스템",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/xtweet",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "xtweet": ["templates/*.html", "static/*"],
    },
    entry_points={
        "console_scripts": [
            "xtweet=xtweet.cli:main",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
) 