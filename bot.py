"""
Leather bastards python bot
"""
from contextlib import closing
from json import load
from logging import basicConfig, INFO, getLogger, info
from os import write, close, remove
from subprocess import Popen, PIPE
from tempfile import mkstemp
from time import sleep

from boto3 import client
from requests import get
# noinspection PyPackageRequirements
from telegram import Bot
from telegram.ext import Updater, CommandHandler, \
    MessageHandler, Filters
from validators import url as validate_url
from os.path import dirname, realpath, join


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


def get_aws_function(text):
    """
    Reqests open API to get url to AWS function that produces audio
    :param text: text to speech
    """
    try:
        response = get("https://nextup.com/ivona/php/nextup-polly"
                       "/CreateSpeech/CreateSpeechGet3.php",
                       allow_redirects=True,
                       params={
                           "voice": "Maxim",
                           "language": "ru-RU",
                           "text": text
                       })
        response.raise_for_status()
        validate_url(response.text)
        return response.text
    except Exception as e:
        raise ApiRequestError("API call error!", e)


def get_audio_by_url(aws_url):
    """
    saves audio produced by aws function to temp file
    """
    try:
        response = get(aws_url, allow_redirects=True)
        response.raise_for_status()
        fd, f = mkstemp(prefix="leather-bastard-")
        write(fd, response.content)
        return fd, f
    except Exception as e:
        raise AwsFunctionError("API call error!", e)


def aws_call(text):
    """
    saves audio produced by aws function to temp file
    """
    response = polly.synthesize_speech(Text=text,
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
        with closing(response["AudioStream"]) as stream:
            fd, f = mkstemp(prefix="leather-bastard-")
            write(fd, stream.read())
            return fd, f
    else:
        raise AwsFunctionError(response)


def cleanup(fd, f):
    """
    Cleans up files
    """
    # noinspection PyBroadException
    try:
        close(fd)
    except Exception:
        pass
    # noinspection PyBroadException
    try:
        remove(f)
    except Exception:
        pass


# noinspection PyUnusedLocal
def echo(update, context):
    """Echo the user message."""
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
    fd = None
    f = None
    try:
        text = update.message.text
        bot.sendMessage(chat_id=ADMIN_CHAT_ID,
                        text="{} asked me to play '{}'"
                        .format(update.message.from_user.name, text))
        if text is None:
            update.message.reply_text("I work only with text :(")
        # url = get_aws_function(text)
        fd, f = aws_call(text)
        process = Popen(["play", "-v", "4.0", "-t", "mp3", f],
                        stdout=PIPE,
                        stderr=PIPE)
        process.wait()
    except Exception as e:
        update.message.reply_text("Oops! {}".format(e))
    finally:
        cleanup(fd, f)


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
