# UCG News Bot

A Discord bot that automatically monitors the [@ucg_en](https://twitter.com/ucg_en) Twitter/X account and posts new tweets to Discord servers using RSSHub.

## Features

- **No Twitter API required!** Uses RSSHub for free access to Twitter feeds
- Monitors Twitter account in real-time
- Posts new tweets to designated Discord channels across multiple servers
- Beautiful Discord embeds with images and tweet metadata
- Automatic deduplication to prevent duplicate posts
- Robust error handling and retry logic
- Persistent state management using SQLite
- Configurable polling interval
- Multi-server support

## Prerequisites

- Python 3.9 or higher
- Discord Bot Token (free)
- **No Twitter API credentials needed!**

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd ucg-news-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your Discord bot token (see Configuration section below).

## Configuration

### Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section and click "Add Bot"
4. Click "Reset Token" to get your bot token
5. Copy the token to your `.env` file as `DISCORD_BOT_TOKEN`
6. Under "Privileged Gateway Intents", you can leave defaults (no special intents needed)

### Generate Bot Invite Link

1. In the Discord Developer Portal, go to "OAuth2" > "URL Generator"
2. Select scopes:
   - `bot`
3. Select bot permissions:
   - Send Messages
   - Embed Links
   - Read Message History
   - View Channels
4. Copy the generated URL and use it to invite the bot to your Discord servers

### Create Target Channel

In each Discord server where you add the bot:
1. Create a text channel named `ucg-news-bot` (or your custom channel name)
2. Ensure the bot has permissions to view and send messages in this channel

### Environment Variables

Edit your `.env` file with the following variables:

```bash
# Required Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Twitter/X Settings (No API key needed!)
TWITTER_USERNAME=ucg_en                # Twitter account to monitor
RSSHUB_INSTANCE=https://rsshub.app     # RSSHub instance URL

# Bot Settings (optional)
POLL_INTERVAL_SECONDS=180              # How often to check for new tweets (seconds)
CHANNEL_NAME=ucg-news-bot              # Discord channel name to post in
LOG_LEVEL=INFO                         # Logging level (DEBUG, INFO, WARNING, ERROR)
DATABASE_PATH=./bot_data.db            # SQLite database path
```

## Usage

### Running Locally

Start the bot:
```bash
python main.py
```

The bot will:
1. Connect to Discord
2. Discover all channels named `ucg-news-bot` in your servers
3. Initialize with the latest tweet (without posting it)
4. Begin polling RSSHub every 3 minutes for new tweets
5. Automatically post new tweets to all configured channels

### Stopping the Bot

Press `Ctrl+C` to gracefully shutdown the bot. The bot will:
- Save its current state
- Close all connections
- Exit cleanly

## How It Works

This bot uses **RSSHub** instead of the Twitter API, which means:
- ✅ Completely free - no API costs
- ✅ No Twitter developer account needed
- ✅ No authentication tokens required
- ✅ Easy to set up and maintain

### Architecture

1. **Polling**: Every 3 minutes (configurable), the bot fetches the RSS feed from RSSHub
2. **Parsing**: RSS entries are parsed to extract tweet content, media, and metadata
3. **Filtering**: Only tweets newer than the last processed tweet ID are selected
4. **Broadcasting**: New tweets are formatted as Discord embeds and sent to all configured channels
5. **State Management**: Tweet IDs are stored in SQLite to prevent duplicates

### RSSHub

RSSHub is an open-source RSS feed generator that supports Twitter and many other platforms:
- Public instance: https://rsshub.app
- Can be self-hosted for better reliability
- Provides RSS feeds for Twitter users without needing API access

## Project Structure

```
ucg-news-bot/
├── main.py                   # Application entry point
├── config.py                 # Configuration loader
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (not in git)
├── .env.example              # Template for environment variables
├── bot/
│   ├── discord_bot.py       # Discord bot implementation
│   ├── twitter_monitor.py   # RSSHub RSS feed client
│   ├── message_formatter.py # Discord embed formatting
│   └── database.py          # SQLite database operations
└── utils/
    ├── logger.py            # Logging configuration
    └── error_handler.py     # Error handling utilities
```

## Deployment

### Local Deployment

Use a process manager like `systemd` (Linux), `launchd` (macOS), or `screen`/`tmux` to keep the bot running:

```bash
# Using screen
screen -S ucg-bot
python main.py
# Press Ctrl+A then D to detach
```

### Cloud Deployment

#### Railway / Render / Fly.io

1. Create a new project
2. Connect your Git repository
3. Add environment variables in the dashboard
4. Deploy

#### Docker

Build the Docker image:
```bash
docker build -t ucg-news-bot .
```

Run the container:
```bash
docker run -d \
  --name ucg-news-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  ucg-news-bot
```

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

#### VPS (DigitalOcean, AWS EC2, etc.)

1. SSH into your server
2. Clone the repository
3. Install Python and dependencies
4. Create a systemd service:

```bash
sudo nano /etc/systemd/system/ucg-news-bot.service
```

```ini
[Unit]
Description=UCG News Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/ucg-news-bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ucg-news-bot
sudo systemctl start ucg-news-bot
sudo systemctl status ucg-news-bot
```

## Troubleshooting

### Bot doesn't post tweets

- Check that RSSHub is accessible: Visit `https://rsshub.app/twitter/user/ucg_en` in your browser
- Verify Twitter username is correct in `.env`
- Check logs for error messages
- Try increasing poll interval if getting rate limited

### Bot can't send messages in Discord

- Verify bot has "Send Messages" and "Embed Links" permissions
- Ensure channel name matches `CHANNEL_NAME` in `.env`
- Check bot role hierarchy in server settings

### Database errors

- Ensure the bot has write permissions in the database directory
- Check that `DATABASE_PATH` is correctly set
- Delete `bot_data.db` to reset (will re-initialize on next run)

### RSSHub errors

- Public RSSHub instance may have rate limits or be temporarily down
- Consider using an alternative instance or self-hosting RSSHub
- Increase `POLL_INTERVAL_SECONDS` to reduce request frequency

### Alternative RSSHub Instances

If `https://rsshub.app` is down or rate-limited, try these alternatives in your `.env`:

```bash
RSSHUB_INSTANCE=https://rsshub.rssforever.com
# or
RSSHUB_INSTANCE=https://rss.fatpandac.com
# or self-host: https://docs.rsshub.app/en/install/
```

## Logging

Logs are output to stdout with timestamps. Log levels:
- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages

Set log level in `.env`:
```bash
LOG_LEVEL=DEBUG
```

## Database

The bot uses SQLite to store:
- Last processed tweet ID
- Discord server list
- Posted tweets (for deduplication, kept for 30 days)

Database location: `./bot_data.db` (configurable)

To reset the bot's state:
```bash
rm bot_data.db
```

## Self-Hosting RSSHub (Optional)

For better reliability and no rate limits, consider self-hosting RSSHub:

1. Follow the [RSSHub installation guide](https://docs.rsshub.app/en/install/)
2. Update your `.env`:
```bash
RSSHUB_INSTANCE=http://localhost:1200
```

Docker example:
```bash
docker run -d --name rsshub -p 1200:1200 diygod/rsshub
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for personal or educational use.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review logs for error messages
3. Open an issue on GitHub

## Advantages over Twitter API

- **Free**: No $100/month Twitter API Essential tier required
- **No authentication**: No need to apply for Twitter developer access
- **Easy setup**: Just need a Discord bot token
- **Reliable**: RSSHub is maintained and widely used
- **Open source**: Both this bot and RSSHub are open source

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- RSS parsing with [feedparser](https://github.com/kurtmckee/feedparser)
- Twitter feeds via [RSSHub](https://github.com/DIYgod/RSSHub)
- Scheduling with [APScheduler](https://github.com/agronholm/apscheduler)
