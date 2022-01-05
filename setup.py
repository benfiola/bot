from setuptools import setup, find_packages


with open("./bot/version.txt", "r") as version_file:
    version = version_file.read()


setup(
    name="bot",
    version=version,
    packages=find_packages(),
    include_package_data=True,
    package_data={"bot": ["version.txt"]},
    install_requires=[
        "alembic==1.7.1",
        "black==21.8b0",
        "click==8.0.1",
        "discord.py[voice]==1.7.3",
        "jinja2==3.0.1",
        "pydantic==1.8.2",
        "pytube==11.0.2",
        "requests==2.26.0",
        "selenium==3.141.0",
        "sqlalchemy==1.4.23",
    ],
    entry_points=dict(console_scripts=["bot-cli=bot.cli:entry_point"]),
)
