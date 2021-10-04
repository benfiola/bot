# bot
Implementation of a generic bot framework.

Intended to accomplish the following objectives:

1. Data persistence
2. Simplified command creation
3. Multi-message conversations
4. Shared API connectivity
5. Platforms as an abstraction
6. Text/audio support

## Design
This framework is primarily centered around four concepts:

1. [*Commands*](./bot/commands): abstractions providing automation driven via user interaction
2. [*Integrations*](./bot/integrations): abstractions exposing common third-party APIs for re-use in commands
3. [*Storage*](./bot/storage): abstractions that provide data persistence across commands
4. [*Platforms*](./bot/platforms): abstractions that facilitate communication.

Ultimately, a central [*Bot*](./bot/main.py) class is what ultimately glues these systems together and allows them to run together.

## Running the bot
The bot can be run either on your local system or within a container.

### Configuration
Configuration is provided via [.ini file](./config.ini.template)

### Running on local system
Ensure the following dependencies are met and on the `PATH`:
* python 3.9.6
* ffmpeg (voice chat)
* libopus-dev (voice chat)
* geckodriver (web automation)
* firefox (web automation)

Then run the following commmand to install the project:

```shell
python -m pip install git+https://github.com/benfiola/bot.git
bot-cli run <config_file>
```

### Running locally via docker
Run the following command:

```shell
docker build -t bot:latest https://github.com/benfiola/bot.git#main
docker run --rm -it -v <config_file>:/config.ini bot:latest 
```

While using docker, keep in mind that the `config_file` path must be absolute.  If working with a relative path, use `${PWD}/<relative_path>`.

### Running programmatically
Use the following example:

```python
import bot
    
# you can instantiate a bot from configuration
async def from_configuration_file(config_file):
    bot.configure_logging()
    config = bot.parse_configuration(config_file)
    my_bot = await bot.Bot.create_from_configuration(config)
    await my_bot.start()

# you can instantiate a bot manually
async def manual():
    bot.configure_logging()
    my_bot = bot.Bot(
        platform=bot.platforms.discord.Platform(bot_token="token"),
        integrations=[
            bot.integrations.youtube.Integration(api_key="api_key")
        ],
        storage=bot.storage.sql.Storage(database_url="url")
    )
    await my_bot.start()
```
