# TG bot and channel based on Python

## TG bot

It's a bot that can monitor the new messages which are matched with the kwywords, and send the message to the group.

This bot is based on `python` and `cloudscraper` package which is a powerful tools to face the anti-crawler mechanism then we can get the data from the RSS feeds.

## TG channel

It's a channel that can monitor the trade message from two website which is also based on the `python` and `cloudscraper` package, it can get the messages about trading information and then send the message to the channel.

## How to use

1. Install the `python` and `cloudscraper` package.
2. Run the `bot.py` to start the bot.
3. Run the `channel.py` to start the channel.

One thing we need to complete is the `TELEGRAM_BOT_TOKEN` and `CHAT_ID` in the `bot.py` and `channel.py` file, these two information can be found in the telegram bot and channel.