try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='obcolumbia',
    version="0.1",
    description="",
    license="GPLv3",
    install_requires=[
    "ebpub",
    "ebdata",
    "obadmin",
    "oauth2>=1.5",
    "pexpect",  # The MUPD scraper uses this to deal with SCP / SFTP.
    ],
    dependency_links=[
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    entry_points="""
    """,
)
