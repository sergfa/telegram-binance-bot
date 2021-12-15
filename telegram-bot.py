#!/usr/bin/env python

import logging
import time
import threading

from telegram import Update,ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

from dotenv import dotenv_values

from binance_client import BinanceClient
from binance_time_utils import convertToStartTime, convertToInterval
from db_manager import DbManager
from utils import symbols_alerts_to_table, symbols_to_table, list_to_tables


env = dotenv_values('.env')

db = DbManager("bot.db")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

MAX_ROWS_IN_TABLE = 50
tickers_ema = {}
bbotHasError = False
supported_tickets = ['BTCUSDT']
sent_signals = {}
db = DbManager("bot.db")
bClient = BinanceClient(testnet=False)
    


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
    chat = job.name.split("_")[0]
    prev_signal = sent_signals.get(job.name, '')
    logger.info(f'subscribe_response for ticket: {ticker}')
    if ticker != 'all':
        prev_signal = sent_signals.get(job.name, '')
        curr_data = tickers_ema.get(ticker, {"buy": False, "sell": False, "fast": -1, "signal": -1})
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
    else:
        alert_data = []
        for ticker_key in tickers_ema:
             curr_data = tickers_ema.get(ticker_key, {"buy": False, "sell": False, "fast": -1, "signal": -1})
             logger.info(f'{ticker_key} Curr data {curr_data}')
             ticker_job_name = f'{chat}_{ticker_key}'
             prev_signal = sent_signals.get(ticker_job_name, '')
             if curr_data['buy'] and prev_signal != 'buy':
                alert_data.append((ticker_key, True, False))
                sent_signals[ticker_job_name] = 'buy'
             elif curr_data['sell'] and  prev_signal != 'sell':
                alert_data.append((ticker_key, False, True))
                sent_signals[ticker_job_name] = 'sell'
        if len(alert_data) > 0:
             #update.message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)        
             tables = list_to_tables(alert_data, MAX_ROWS_IN_TABLE, symbols_alerts_to_table)
             for table in tables:
                context.bot.send_message(job.context, text=f'{table}', parse_mode=ParseMode.HTML)
        else:
            logger.info(f'No new alert for job {job.name}')     
             

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
        if ticker !='all' and ticker not in supported_tickets:
            update.message.reply_text(f'Sorry we can not subscribe to your ticker! Please use one of the supported tickets or all,to get all supported tickers Use  /list')
            return

        job_name = f'{str(chat_id)}_{ticker}'
        job_removed = remove_job_if_exists(name=job_name, context=context)
        # context.job_queue.run_once(alarm, due, context=chat_id, name=str(chat_id))
        context.job_queue.run_repeating(subscribe_response, 300, context=chat_id, name=job_name)
        db.insertJob(str(chat_id), ticker)
        

        text = f'You successfully subscribed to ticker: {ticker}'
        if job_removed:
            text += ' Old one was removed.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /subscribe <ticker|all>')

def status(update: Update, context: CallbackContext) -> None:
    """ Get status of the bot"""
    global bbotHasError
    status_message = f'Error: {bbotHasError}' 
    update.message.reply_text(status_message)

def list(update: Update, context: CallbackContext) -> None:
    """ Get all tickers"""
    tables  = list_to_tables(supported_tickets, MAX_ROWS_IN_TABLE, symbols_to_table) 
    for table in tables:
        update.message.reply_text(f'{table}',  parse_mode=ParseMode.HTML)

def ticker(update: Update, context: CallbackContext) -> None:
    """Get ticker info."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the ticker
        ticker = str(context.args[0])
        if ticker != 'all' and ticker not in supported_tickets:
            update.message.reply_text(f'Sorry we can not get info about your ticker! Please use one of the supported tickets or all,To get all tickets use /list')
            return
        if ticker != 'all':
            curr_data = tickers_ema.get(ticker, {"buy": False, "sell": False, "fast": -1, "signal": -1})
            text = f'Ticker {ticker} info: Buy: {curr_data["buy"]}, Sell: {curr_data["sell"]}, EMA fast: {curr_data["fast"]}, EMA Signal: {curr_data["signal"]}'
            update.message.reply_text(text)
        else:
            tickers_data = []
            for ticker_key in tickers_ema:
                curr_data = tickers_ema.get(ticker_key, {"buy": False, "sell": False, "fast": -1, "signal": -1}) 
                tickers_data.append((ticker_key, curr_data["buy"], curr_data["sell"]))
            
            tables = list_to_tables(tickers_data, MAX_ROWS_IN_TABLE, symbols_alerts_to_table)
            for table in tables:
                update.message.reply_text(f'{table}',  parse_mode=ParseMode.HTML)
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /ticker <ticker>')



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
    try:
        db.deleteJob(str(chat_id), ticker)
    except Exception:
        logger.error(f'Failed to delete job from db for chat: {chat_id}, ticker: {ticker}')   


def runBBot(config, interval, start, tickers, bClient):
    global tickers_ema, bbotHasError
    intervalStr = convertToInterval(interval,'d')
    startStr=convertToStartTime(start, 'days')
    cycle = 0
    while (config["keepRunning"]):
        cycle +=1
        logger.info(f'Running step #{cycle}')
        try:
            tickers_ema = bClient.ema_checker(interval=intervalStr, start=startStr, tickers=tickers)
            logger.info(f'Ema results #{tickers_ema}')
            bbotHasError = False                   
        except Exception:
            logger.exception("An exception was thrown!")
            bbotHasError = True   
        time.sleep(3600)

def __runBBot__(config):
    runBBot(config,1, 30, supported_tickets, bClient) 

def loadJobs(updater: Updater, db: DbManager) -> None:
    jobs = db.getJobs()
    if len(jobs) > 0:
        for job in jobs:
            job_name = f'{str(job[1])}_{job[2]}'
            updater.job_queue.run_repeating(subscribe_response, 300, context=job[1], name=job_name)
            logger.info(f'Add job from db {job}')
    
def main() -> None:
    """Run bot."""
    global supported_tickets
    
    logger.info('Start running ema bot')
    supported_tickets = bClient.get_usdt_tickers()[:10]
    emaBotConfig = {"keepRunning": True}
    run_app_thread = threading.Thread(target=__runBBot__, args=(emaBotConfig,))
    run_app_thread.start()
    
    
    # Create the Updater and pass it your bot's token.
    token = env["TELEGRAM_BOT_TOKEN"]
    updater = Updater(token)
    logger.info("Loading jobs from db...")
    loadJobs(updater, db)
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("subscribe", subscribe))
    dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("ticker", ticker))
    dispatcher.add_handler(CommandHandler("list", list))
    
    
    

    # Start the Bot
    logger.info('Start running telegram bot')
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()
    emaBotConfig["keepRunning"] = False
    logger.info(f'Exiting from telegram bot...')


if __name__ == '__main__':
    main()
