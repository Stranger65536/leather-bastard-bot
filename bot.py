"""
Leather bastards python bot
"""
import subprocess
from contextlib import closing
from datetime import datetime
from json import load
from logging import basicConfig, INFO, getLogger, info
from os import remove
from os.path import dirname, realpath, join
from time import sleep

from boto3 import client
# noinspection PyPackageRequirements
from telegram import Bot
from telegram.ext import Updater, CommandHandler, \
    MessageHandler, Filters

AWS_KEY = 'your_token_here'
AWS_SECRET_ACCESS_KEY = 'your_secret_access_key_here'
TELEGRAM_TOKEN = "your_telegram_token_here"
ADMIN_CHAT_ID = "your_admin_chat_id"

dir_name = dirname(realpath(__file__))

basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=INFO)

logger = getLogger(__name__)

polly = client('polly',
               aws_access_key_id=AWS_KEY,
               region_name='us-west-2',
               aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

bot = Bot(token=TELEGRAM_TOKEN)


class ApiRequestError(Exception):
    """
    Identifies exception of calling open API
    """
    pass


class AwsFunctionError(Exception):
    """
    Identifies exception of calling AWS funciton
    """
    pass


# noinspection PyUnusedLocal
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! Just type a text and I\'ll '
                              'play it on device')


# noinspection PyUnusedLocal
def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help is on the way! '
                              'Just type a text and I\'ll '
                              'play it on device')


def aws_call(text):
    """
    saves audio produced by aws function to temp file
    """
    response = polly.synthesize_speech(Text=f"<speak>{text}</speak>",
                                       TextType="ssml",
                                       OutputFormat="mp3",
                                       SampleRate="24000",
                                       LanguageCode="ru-RU",
                                       VoiceId="Maxim")
    # Access the audio stream from the response
    if "AudioStream" in response:
        # Note: Closing the stream is important because the
        # service throttles on the number of parallel connections.
        # Here we are using contextlib.closing to ensure the close
        # method of the stream object will be called automatically
        # at the end of the with statement's scope.
        tmp_dir = dirname(realpath(__file__))
        now = str(datetime.now()).replace(" ", "_")
        file = f"{tmp_dir}/leather-bastard-{now}"
        with closing(response["AudioStream"]) as stream:
            arr = stream.read()
            with open(file, mode="wb") as f:
                f.write(arr)
        return file
    else:
        raise AwsFunctionError(response)


def cleanup(f):
    """
    Cleans up files
    """
    # noinspection PyBroadException
    try:
        remove(f)
    except Exception:
        pass


sound = "1.0"


# noinspection PyUnusedLocal
def echo(update, context):
    """Echo the user message."""
    global sound
    info(update.message)
    with open(join(dir_name, "whitelist.json"), "r") as f:
        whitelist = load(f)
    if update.message.from_user.name not in whitelist:
        bot.sendMessage(chat_id=ADMIN_CHAT_ID,
                        text="{} tries to reach me"
                        .format(update.message.from_user.name))
        return
    if update.message.text.strip() == 'ping':
        bot.sendMessage(chat_id=ADMIN_CHAT_ID,
                        text="{} pinged me"
                        .format(update.message.from_user.name))
        update.message.reply_text("Pong")
        return
    if update.message.text.strip() == 'sound':
        update.message.reply_text(text="sound: " + sound)
        return
    if update.message.text.strip().startswith("sound"):
        sound = update.message.text.strip().split(" ")[-1]
        update.message.reply_text(text="sound: " + sound)
        return
    f = None
    try:
        text = update.message.text
        bot.sendMessage(chat_id=ADMIN_CHAT_ID,
                        text="{} asked me to play '{}'"
                        .format(update.message.from_user.name, text))
        if text is None:
            update.message.reply_text("I work only with text :(")
        f = aws_call(text)
        # noinspection PyBroadException
        res = subprocess.run(["play", "-v", sound, "-t", "mp3", f],
                             check=True, shell=False)
        with open(f, "rb") as f:
            bot.sendAudio(chat_id=ADMIN_CHAT_ID, audio=f,
                          reply_to_message_id=update.message.message_id)
    except Exception as e:
        update.message.reply_text("Oops! {}".format(e))
    finally:
        cleanup(f)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN,
                      use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    # updater.idle()
    while True:
        sleep(1)


if __name__ == '__main__':
    main()
