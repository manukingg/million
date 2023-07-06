import telebot
from telebot import types
import json
from datetime import datetime, timedelta
import datetime
import base64
from dateutil.relativedelta import relativedelta
from mixpanel import Mixpanel
from cryptomus import Client
import db as dbu
from settlement import get_invoice_json
import random
import http.client
import hashlib

with open('texts.json', 'r') as json_file:
    text = json.load(json_file)

# API's
bot = telebot.TeleBot('6099520315:AAHx6SjHmf5o-nq1tsZRrsfKw8IqCe4Fgr8')  # telebot API
DB_TABLE_NAME = 'users_info_ru'
mp = Mixpanel('ba4f4c87c35eabfbb7820e21724aaa26')
PAYMENT_KEY = 'y4FWxjLLtiR16WEsiHydXAyQ6PQioKKDwW8ECjMgQa7tj7DulwWfSoyh8gbJmdXtRaCkS6k7QqE8fX1BxJOtUJ4MRoNkPQAWQUKQDCrOmVQwuCBpY5pKvEJO3P6wSomL'
MERCHANT_UUID = '3b89f29b-2459-4bbd-bace-2f2e14df7aed'
payment = Client.payout(PAYMENT_KEY, MERCHANT_UUID)
API_BASE_URL = "https://api.cryptomus.com/v1"
CREATE_INVOICE_ENDPOINT = "/payment"

# BUTTONS
button_home = types.InlineKeyboardButton(text['button_home'], callback_data='home')
button_purchase = types.InlineKeyboardButton(text['button_buy'], callback_data='purchase')
button_manage = types.InlineKeyboardButton(text['button_manage'], callback_data='manage')
button_instructions = types.InlineKeyboardButton(text['button_instructions'], callback_data='instructions')
button_about = types.InlineKeyboardButton(text['button_about'], callback_data='about')
button_prolongate = types.InlineKeyboardButton(text['button_prolongate'], callback_data='prolongate')
button_monthly = types.InlineKeyboardButton(text=text['button_monthly'], callback_data='monthly_subscription')
button_daily = types.InlineKeyboardButton(text=text['button_daily'], callback_data='daily_subscription')
button_Nuremberg = types.InlineKeyboardButton(text['nuremberg'], callback_data='nbg1')
button_Helsinki = types.InlineKeyboardButton(text['helsinki'], callback_data='hel1')
button_Moscow = types.InlineKeyboardButton(text['moscow'], callback_data='msk1')
button_Falkenstein = types.InlineKeyboardButton(text['falkenstein'], callback_data='fsn1')
button_crypto = types.InlineKeyboardButton(text['button_crypto'], callback_data='crypto_payment')
button_ios = types.InlineKeyboardButton(text='iOS', url='https://itunes.apple.com/us/app/outline-app/id1356177741')
button_android = types.InlineKeyboardButton(
    text='Android', url='https://play.google.com/store/apps/details?id=org.outline.android.client')
button_macos = types.InlineKeyboardButton(text='MacOS', url='https://itunes.apple.com/us/app/outline-app/id1356178125')
button_windows = types.InlineKeyboardButton(
    text='Windows', url='https://s3.amazonaws.com/outline-releases/client/windows/stable/Outline-Client.exe')
button_linux = types.InlineKeyboardButton(
    text='Linux', url='https://s3.amazonaws.com/outline-releases/client/linux/stable/Outline-Client.AppImage')

def create_invoice(cursor, chat_id, days, price):
    chat_id = str(chat_id)
    conn = http.client.HTTPSConnection("api.cryptomus.com")
    payload = json.dumps({
        'amount': price,
        'currency': 'USD',
        'order_id': str(random.randint(10000, 100000)),
        'url_return': 'https://t.me/HumanVPN_ru_bot',
        'url_callback': 'https://t.me/HumanVPN_ru_bot',
        'accuracy_payment_percent': '1'        
    })
    payload_base64 = base64.b64encode(payload.encode('utf-8'))
    data_to_hash = payload_base64 + PAYMENT_KEY.encode('utf-8')
    md5_hash = hashlib.md5(data_to_hash).hexdigest()
    headers = {
        'merchant': MERCHANT_UUID,
        'sign': md5_hash,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/v1/payment", payload, headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    json_data = json.loads(data)
    hosted_url = json_data['result']['url']
    invoice_status = json_data['result']['payment_status']
    invoice_id = json_data['result']['order_id']
    expires_at = datetime.datetime.fromtimestamp(json_data['result']['expired_at'])
    created_at = expires_at - timedelta(hours=1)
    dbu.update(cursor, 'INSERT INTO invoices (id, chat_id, status, duration_days, created_at, expires_at, hosted_url)'
               ' VALUES (%s, %s, %s, %s, %s, %s, %s)',
               invoice_id, chat_id, invoice_status, days, created_at, expires_at, hosted_url)
    return hosted_url


@bot.message_handler(commands=['start'])
def send_welcome(message):
    source = message.text.split(' ')[1] if len(message.text.split(' ')) > 1 else 'dW5rbm93bg=='
    source = base64.b64decode(source).decode('utf-8')
    connection = dbu.connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        query = """SELECT chat_id FROM users_info_ru WHERE chat_id = (%s)"""
        chat_id = message.chat.id
        username = message.from_user.username
        cursor.execute(query, (chat_id,))
        result = cursor.fetchone()
        if result is None:
            dbu.update(cursor, "INSERT INTO users_info_ru (chat_id, user_nickname) VALUES (%s, %s)", chat_id, username)
            dbu.update(cursor, "INSERT INTO analytics (chat_id, source) VALUES (%s, %s)", chat_id, source)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(button_purchase, button_manage, button_instructions, button_about)
        bot.send_message(message.chat.id, text['home'], parse_mode='html', reply_markup=markup)
        mp.people_set(str(message.chat.id), {
            '$First_name': f'{message.from_user.first_name}',
            '$Last_name': f'{message.from_user.last_name}',
            '$Nickname': f'{username}',
            '$Source': f'{source}'        
        }, meta = {'$ignore_time': True, '$ip': 0})
        mp.track(str(message.chat.id), 'User started bot', {'Source': f'{source}'})
    finally:
        connection.commit()
        connection.close()

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    connection = dbu.connection_pool.get_connection()
    try:
        cursor = connection.cursor()

        if call.data == 'home':
            chat_id = str(call.message.chat.id)
            
            server_ip = dbu.fetch_one_for_query(cursor, 'SELECT server_ip FROM users_info_ru WHERE chat_id = %s', chat_id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            if server_ip == None:
                markup.add(button_purchase, button_manage, button_instructions, button_about)
            else:
                markup.add(button_prolongate, button_manage, button_instructions, button_about)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['home'], reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User came home', {'Button name': f'{call.data}'})


    # Purchase logics --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

        if call.data == 'purchase':
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_monthly, button_daily, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['purchase'], reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered Purchase category', {'Button name': 'Purchase'})

        if call.data == 'monthly_subscription' or call.data == 'daily_subscription':
            chat_id = str(call.message.chat.id)
            days = {
                "monthly_subscription": 31,
                "daily_subscription": 1
            }
            amount = {
                "monthly_subscription": 4.99,
                "daily_subscription": 0.99
            }
            dbu.update(cursor, 'UPDATE users_info_ru SET duration_days = %s, amount = %s WHERE chat_id = %s', days[call.data], amount[call.data], chat_id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_crypto, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['method'], reply_markup=markup)
            mp.track(str(call.message.chat.id), f'User chose {call.data}', {'Button name': f'{call.data}'})

        if call.data == 'crypto_payment':
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_Nuremberg, button_Falkenstein, button_Helsinki,button_Moscow, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['location'], reply_markup=markup)
            mp.track(str(call.message.chat.id), f'User chose {call.data}', {'Button name': f'{call.data}'})


        if call.data == 'nbg1' or call.data == 'hel1' or call.data == 'fsn1' or call.data == 'msk1':
            chat_id = str(call.message.chat.id)
            dbu.update(cursor, 'UPDATE users_info_ru SET server_location = %s WHERE chat_id = %s',
                    call.data, call.message.chat.id)
            amount = str(dbu.fetch_one_for_query(cursor, 'SELECT amount FROM users_info_ru WHERE chat_id = %s', chat_id))
            duration = str(dbu.fetch_one_for_query(cursor, 'SELECT duration_days FROM users_info_ru WHERE chat_id = %s', chat_id))
            hosted_url = create_invoice(cursor, call.message.chat.id, duration, amount)
            markup = types.InlineKeyboardMarkup()
            markup.add(button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['invoice'].format(hosted_url=hosted_url), parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), f'User chose server {call.data}', {'Button name': f'{call.data}'})

        # Manage my account logics

        if call.data == 'manage':
            chat_id = str(call.message.chat.id)
            expiration_date, server_ip = dbu.fetch_row_for_query(
                cursor, 'SELECT expiration_date, server_ip FROM users_info_ru WHERE chat_id = %s', chat_id)
            now = datetime.datetime.now()
            if expiration_date is not None and expiration_date > now:
                if server_ip is None:
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(button_instructions, button_home)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text['server_creating'], parse_mode='html', reply_markup=markup)
                    mp.track(str(call.message.chat.id), 'User entered Profile section while server was creating', {'Button name': 'Manage', 'Ordered untill': f'{expiration_date}'})
                else:
                    username = call.from_user.username
                    shadowsocks_link = dbu.fetch_one_for_query(
                        cursor, 'SELECT link FROM users_info_ru WHERE chat_id = %s', chat_id)
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(button_instructions, button_home)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text['profile'].format(
                        username=username, ordered_untill=expiration_date, users_link=shadowsocks_link), parse_mode='html', reply_markup=markup)
                    mp.track(str(call.message.chat.id), 'User entered Profile section while active subscription', {'Button name': 'Manage', 'Ordered untill': f'{expiration_date}'})
            else:
                invoice_count = dbu.fetch_one_for_query(
                    cursor, 'SELECT COUNT(*) from invoices where chat_id = %s and status = %s', chat_id, 'check')
                if invoice_count > 0:
                    hosted_url = dbu.fetch_one_for_query(
                        cursor, 'SELECT hosted_url from invoices where chat_id = %s and status = %s order by created_at desc limit 1', chat_id, 'check')
                    markup = types.InlineKeyboardMarkup()
                    button_invoice = types.InlineKeyboardButton(text='Ссылка на счёт', url=str(hosted_url))
                    markup.add(button_invoice, button_home)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                        text=text['invoice_unpayed'], parse_mode='html', reply_markup=markup)
                    mp.track(str(call.message.chat.id), 'User entered Profile section with unpayed invoice', {'Button name': 'Profile'})
                else:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(button_home)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                        text=text['invoice_uncreated'], parse_mode='html', reply_markup=markup)
                    mp.track(str(call.message.chat.id), 'User entered Profile section before creating invoice', {'Button name': 'Profile'})

        if call.data == 'instructions':
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_ios, button_android, button_macos, button_windows, button_linux, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['instructions'], parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered instructions section', {'Button name': 'Instructions'})

        if call.data == 'prolongate':
            pass

        if call.data == 'about':
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_instructions, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=text['about'], parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered About section', {'Button name': 'About'})

    finally:
        connection.commit()
        connection.close()
# Second level logics----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

bot.infinity_polling()
