# Leather bastards bot
Allows you to play text messages send to Telegram on the device with bot running

## Installation
- You need python 3.6+ to run this bot.
- `pip3 install -r requirements.txt`
- in bot.py, you have to put `AWS_KEY`, `TELEGRAM_TOKEN` and `ADMIN_CHAT_ID`. They correspond to your AWS API key, your registered telegram bot access token, and ID of telegram chat to send verbose messages to.
- `whitelist.json` has to be populated with nicknames (starts with @) of users who allowed to use this bot. Other users access is logged in verbose chat.
