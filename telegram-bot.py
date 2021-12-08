#!/usr/bin/env python

import logging
import time
import threading

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from dotenv import dotenv_values

from binance_client import BinanceClient
from binance_time_utils import convertToStartTime, convertToInterval

env = dotenv_values('.env')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


tickers_ema = {}
bbotHasError = False
supported_tickets = ['BTCUSDT']
sent_signals = {}


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
# Best practice would be to replace context with an underscore,
# since context is an unused local variable.
# This being an example and not having context present confusing beginners,
# we decided to have it present as context.
def start(update: Update, context: CallbackContext) -> None:
    """Sends explanation on how to use the bot."""
    update.message.reply_text('Hi! Use /subscribe <ticker> to get buy/sell signal')


def subscribe_response(context: CallbackContext) -> None:
    """Send the alarm message."""
    global tickers_ema, bbotHasError, supported_tickets, sent_signals
    job = context.job
    ticker = job.name.split("_")[1]
    prev_signal = sent_signals.get(job.name, '')
    logger.info(f'subscribe_response for ticket: {ticker}')
    curr_data = tickers_ema.get(ticker, {"buy": False, "sell": False})
    logger.info(f'subscribe_response current ema data: {curr_data}, prev signal: { prev_signal}')
    if bbotHasError:
        logger.info(f'subscribe_response bot has error, response will not be sent')
        return
    if curr_data['buy'] and prev_signal != 'buy':
        context.bot.send_message(job.context, text=f'BUY ALERT {ticker}')
        sent_signals[job.name] = 'buy'
    elif curr_data['sell'] and  prev_signal != 'sell':
        context.bot.send_message(job.context, text=f'SELL ALERT {ticker}')
        sent_signals[job.name] = 'sell'
             

def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def subscribe(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the ticker
        ticker = str(context.args[0])
        if ticker not in supported_tickets:
            update.message.reply_text(f'Sorry we can not subscribe to your ticker! Please use one of the supported tickets: {supported_tickets}')
            return

        job_name = f'{str(chat_id)}_{ticker}'
        job_removed = remove_job_if_exists(name=job_name, context=context)
        # context.job_queue.run_once(alarm, due, context=chat_id, name=str(chat_id))
        context.job_queue.run_repeating(subscribe_response, 60, context=chat_id, name=job_name)
        

        text = f'You successfully subscribed to ticker: {ticker}'
        if job_removed:
            text += ' Old one was removed.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /subscribe <ticker>')


def unsubscribe(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    global sent_signals
    chat_id = update.message.chat_id
    ticker = str(context.args[0])
    if not (ticker and ticker.strip()):
        update.message.reply_text('Sorry we can not guess your ticker! Usage: /unsubscribe <ticker>')
        return

    job_name = f'{str(chat_id)}_{ticker}'
    job_removed = remove_job_if_exists(name=job_name, context= context)
    sent_signals.pop(job_name, None) 
    text = f'You successfully unsubscribed from {ticker}' if job_removed else f'You have no active signal for ticker {ticker}'
    update.message.reply_text(text)


def runBBot(interval, start, tickers):
    global tickers_ema, bbotHasError, supported_tickets
    bClient = BinanceClient(testnet=True)
    intervalStr = convertToInterval(interval,'h')
    startStr=convertToStartTime(start, 'hours')
    cycle = 0
    while (True):
        cycle +=1
        logger.info(f'Running step #{cycle}')
        try:
            tickers_ema = bClient.ema_checker(interval=intervalStr, start=startStr, tickers=tickers)
            logger.info(f'Ema results #{tickers_ema}')
            bbotHasError = False                   
        except Exception:
            logger.exception("An exception was thrown!")
            bbotHasError = True   
        time.sleep(60)

def __runBBot__():
    runBBot(1, 240, ['BTCUSDT']) 

def main() -> None:
    """Run bot."""

    logger.info('Start running ema bot')
    run_app_thread = threading.Thread(target=__runBBot__)
    run_app_thread.start()
    # Create the Updater and pass it your bot's token.
    token = env["TELEGRAM_BOT_TOKEN"]
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("subscribe", subscribe))
    dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Start the Bot
    logger.info('Start running telegram bot')
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()