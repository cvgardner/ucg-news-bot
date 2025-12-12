# UCG News Bot

A stateless Discord bot that monitors multiple Ultraman Card Game (UCG) news sources and automatically posts updates to Discord channels. Runs as a GitHub Actions cron job every 15 minutes.

## Features

- **🤖 Fully Automated**: Runs on GitHub Actions - no server required
- **📡 Multi-Source Monitoring**:
  - X/Twitter ([@ucg_en](https://twitter.com/ucg_en))
  - YouTube (@ultramancardgame_official)
  - Ultraman Columns (official API)
  - Ultraman News (official API)
- **💬 Automatic Thread Creation**: Creates discussion threads for each post
- **🔄 Smart Deduplication**: Prevents duplicate posts using SQLite database
- **🌐 Multi-Server Support**: Posts to all Discord servers with configured channel name
- **⚡ Stateless Design**: Quick execution (~5-10 seconds per run)
- **🔒 Secure**: API credentials stored as GitHub secrets
- **📊 Cost Effective**: Free tier GitHub Actions (2,000 minutes/month)

## Architecture

Unlike traditional Discord bots that run 24/7, this bot uses a **stateless cron approach**:

1. **GitHub Actions** triggers the bot every 15 minutes
2. Bot checks all configured sources for new content
3. Posts new content to Discord channels (by name: `ucg-news-bot`)
4. Updates database and exits
5. Database persists between runs via GitHub Actions artifacts

**Benefits**:
- No server hosting costs
- No uptime management
- Reliable execution via GitHub's infrastructure
- Easy to maintain and debug

## Prerequisites

- Discord Bot Token
- X/Twitter API Bearer Token (for @ucg_en monitoring)
- YouTube Data API v3 Key (for YouTube monitoring)
- GitHub account (for Actions hosting)

## Quick Start

### 1. Fork/Clone Repository

```bash
git clone https://github.com/yourusername/ucg-news-bot.git
cd ucg-news-bot
```

### 2. Set Up Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token (you'll need this for GitHub secrets)
5. Under "Privileged Gateway Intents", enable:
   - ✅ Server Members Intent
   - ✅ Message Content Intent (optional)

### 3. Generate Bot Invite Link

1. In Discord Developer Portal, go to "OAuth2" > "URL Generator"
2. Select scopes:
   - `bot`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Create Public Threads
   - ✅ Send Messages in Threads
   - ✅ View Channels
4. Copy the generated URL and invite the bot to your Discord server(s)

### 4. Create Discord Channel

In each Discord server where you added the bot:
1. Create a text channel named `ucg-news-bot`
2. Ensure the bot has permissions to view and send messages

### 5. Get API Credentials

#### X/Twitter API
1. Go to [X Developer Portal](https://developer.twitter.com/)
2. Create a new app (Free tier is sufficient)
3. Copy your Bearer Token

#### YouTube Data API v3
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create credentials (API Key)
5. Copy the API key

### 6. Configure GitHub Secrets

In your GitHub repository, you only need to add **3 secrets** (actual credentials):

1. Go to **Settings** > **Secrets and variables** > **Actions**
2. Click **"New repository secret"** and add each of the following:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | `ODc0NDI2MDg5MDA...` |
| `X_API_BEARER` | X/Twitter API Bearer token | `AAAAAAAAAAAAA...` |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | `AIzaSyD4YjC4R...` |

**Note**: Public identifiers (channel IDs, usernames, URLs) are already hardcoded in the workflow file - you don't need to add them as secrets!

### 7. Enable GitHub Actions

1. Go to your repository's **Actions** tab
2. If prompted, click **"I understand my workflows, go ahead and enable them"**
3. The workflow will run automatically every 15 minutes
4. You can also trigger it manually:
   - Go to **Actions** > **UCG News Bot**
   - Click **"Run workflow"** > **"Run workflow"**

## Local Development & Testing

### Setup Local Environment

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your credentials:
```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
CHANNEL_NAME=ucg-news-bot
X_API_BEARER=your_x_api_bearer_token_here
UCG_EN_X_ID=1798233243185303552
TWITTER_USERNAME=ucg_en
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_CHANNEL_ID=UC0WwX8aoBWRAdQ2bM-FD8TQ
ULTRAMAN_COLUMN_URL=https://ultraman-cardgame.com/page/us/column/column-list
ULTRAMAN_NEWS_URL=https://ultraman-cardgame.com/page/us/news/news-list
LOG_LEVEL=INFO
DATABASE_PATH=./bot_data.db
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Run Locally

Execute the cron script:
```bash
python run_cron.py
```

This will:
1. Check all configured sources for new content
2. Post any new content to Discord
3. Update the database
4. Exit

### Test Individual Sources

Use the test script to check specific sources:
```bash
python test_discord_post.py
```

Then select which source to test:
- 1: Ultraman Columns
- 2: Ultraman News
- 3: X/Twitter
- 4: YouTube

## Project Structure

```
ucg-news-bot/
├── run_cron.py                   # Main entry point for cron execution
├── config.py                     # Configuration loader
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .github/
│   └── workflows/
│       └── news-bot.yml         # GitHub Actions workflow
├── bot/
│   ├── news_publisher.py        # Stateless news publisher
│   ├── x_api.py                 # X/Twitter API client
│   ├── youtube_api.py           # YouTube Data API client
│   ├── ultraman_column_api.py   # Ultraman Columns API client
│   ├── ultraman_news_api.py     # Ultraman News API client
│   └── database.py              # SQLite database operations
└── utils/
    ├── logger.py                # Logging configuration
    └── error_handler.py         # Error handling utilities
```

## How It Works

### GitHub Actions Workflow

The workflow (`.github/workflows/news-bot.yml`) runs every 15 minutes:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:        # Manual trigger
```

**Workflow Steps**:
1. **Checkout code**: Gets the latest code from repository
2. **Set up Python**: Installs Python 3.11
3. **Install dependencies**: Installs required packages
4. **Download database**: Retrieves database from previous run (via artifacts)
5. **Run news check**: Executes `run_cron.py` with secrets as environment variables
6. **Upload database**: Saves updated database for next run

### Database Persistence

Since GitHub Actions are stateless, the database is preserved using **artifacts**:
- After each run, `bot_data.db` is uploaded as an artifact
- Before each run, the previous database is downloaded
- Artifacts are kept for 7 days
- This prevents duplicate posts across runs

### Source Monitoring

Each source is checked sequentially:

**X/Twitter** (`bot/x_api.py`):
- Uses X API v2 to fetch latest tweets from @ucg_en
- Filters for [EN] tweets if needed
- Returns tweet URL

**YouTube** (`bot/youtube_api.py`):
- Uses YouTube Data API v3 search endpoint
- Fetches latest videos from channel
- Filters for [EN] videos
- Returns video URL

**Ultraman Columns** (`bot/ultraman_column_api.py`):
- Calls unofficial Ultraman API endpoint
- Fetches latest column articles
- Returns article URL

**Ultraman News** (`bot/ultraman_news_api.py`):
- Calls unofficial Ultraman API endpoint
- Fetches latest news articles
- Filters out pinned articles
- Returns article URL

### Deduplication

The SQLite database (`bot_data.db`) tracks posted content:

```sql
CREATE TABLE posted_content (
    url TEXT PRIMARY KEY,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT
);
```

Before posting, the bot checks if the URL already exists in the database.

### Discord Posting

When new content is found:
1. Bot connects to Discord
2. Discovers all channels named `ucg-news-bot` across all servers
3. Posts the URL to each channel
4. Creates a discussion thread for each post (24-hour auto-archive)
5. Marks the URL as posted in the database
6. Disconnects and exits

## Configuration

### Channel Name

By default, the bot posts to channels named `ucg-news-bot`. To change this, update the workflow:

```yaml
env:
  CHANNEL_NAME: your-custom-channel-name
```

### Cron Schedule

To change how often the bot runs, edit `.github/workflows/news-bot.yml`:

```yaml
on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes
    # or
    - cron: '0 * * * *'     # Every hour
```

[Cron syntax reference](https://crontab.guru/)

### Enable/Disable Sources

To disable a source, remove its credentials from GitHub secrets. The bot will skip sources with missing credentials.

## Monitoring

### Check Workflow Runs

1. Go to **Actions** tab in your repository
2. Click on **UCG News Bot** workflow
3. View recent runs and their logs

### Logs

Each workflow run produces detailed logs:
- Source checking progress
- New posts found
- Discord posting results
- Errors and warnings

### Manual Trigger

To test or force a check:
1. Go to **Actions** > **UCG News Bot**
2. Click **"Run workflow"**
3. Select branch and click **"Run workflow"**

## Troubleshooting

### Bot Not Posting

**Check workflow is running**:
- Go to Actions tab
- Verify recent runs exist
- Check for error messages in logs

**Verify secrets are set**:
- Settings > Secrets and variables > Actions
- Ensure all required secrets exist

**Check Discord permissions**:
- Bot has "Send Messages" permission
- Bot has "Create Public Threads" permission
- Channel named `ucg-news-bot` exists

### API Rate Limits

**X API**: Free tier has strict rate limits
- Default: 50 requests per 15 minutes
- Bot checks once per 15 minutes (96 times/day)
- Should stay within limits

**YouTube API**: Daily quota limits
- Each search costs ~100 quota units
- Daily quota: 10,000 units
- Bot checks every 15 minutes = 96 checks/day = ~9,600 units
- Should stay within limits

### Database Not Persisting

**Check artifact upload/download**:
- Verify "Upload database artifact" step succeeds
- Check "Download previous database" doesn't fail
- Artifacts expire after 7 days (adjust if needed)

### No Channels Found

**Error**: `No channels named 'ucg-news-bot' found in any guilds`

**Solutions**:
1. Create a channel named `ucg-news-bot` in your Discord server
2. Verify bot is in the server (check bot's server list)
3. Ensure bot has "View Channels" permission

## Cost Estimate

### GitHub Actions (Free Tier)
- **Monthly limit**: 2,000 minutes
- **Bot runtime**: ~8 seconds per run
- **Runs per month**: 2,880 (96/day × 30 days)
- **Total usage**: ~384 minutes/month
- **Cost**: **FREE** ✅

### API Costs
- **X API Free Tier**: 50 requests per 15 min - **FREE** ✅
- **YouTube Data API Free Tier**: 10,000 quota units/day - **FREE** ✅
- **Ultraman APIs**: Unofficial, no rate limits - **FREE** ✅

**Total monthly cost: $0** 🎉

## Security Best Practices

✅ **Never commit credentials** to git
✅ **Use GitHub Secrets** for all API keys
✅ **.env file is in .gitignore**
✅ **.env.example has placeholders** only
✅ **Bot token has minimal permissions**

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test locally with `python run_cron.py`
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is provided as-is for personal or educational use.

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- X/Twitter integration via [X API v2](https://developer.twitter.com/en/docs/twitter-api)
- YouTube integration via [YouTube Data API v3](https://developers.google.com/youtube/v3)
- Automated with [GitHub Actions](https://github.com/features/actions)

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review workflow logs in GitHub Actions
3. Open an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Workflow run link (if applicable)

---

**Enjoy automated UCG news updates!** 🎮✨
