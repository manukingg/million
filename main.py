import telebot
from telebot import types
import json
from datetime import datetime, timedelta
from telebot.types import LabeledPrice, ShippingOption
import datetime
import base64
from dateutil.relativedelta import relativedelta
from mixpanel import Mixpanel
from cryptomus import Client
import db as dbu
from settlement import get_invoice_json, TRIAL_SERVER_IPS
import random
import http.client
import hashlib
import requests
import time
import uuid
from google.cloud import storage


with open('texts.json', 'r') as json_file:
    text = json.load(json_file)

with open('locations.json', 'r') as json_file_locations:
    locations = json.load(json_file_locations)

with open('trial_servers.json', 'r') as json_file_trial_locations:
    trial_locations = json.load(json_file_trial_locations)

# API's
bot = telebot.TeleBot('6099520315:AAHx6SjHmf5o-nq1tsZRrsfKw8IqCe4Fgr8')  # telebot API
payment_token = '381764678:TEST:63821'
DB_TABLE_NAME = 'users_info_ru'
mp = Mixpanel('ba4f4c87c35eabfbb7820e21724aaa26')
PAYMENT_KEY = 'y4FWxjLLtiR16WEsiHydXAyQ6PQioKKDwW8ECjMgQa7tj7DulwWfSoyh8gbJmdXtRaCkS6k7QqE8fX1BxJOtUJ4MRoNkPQAWQUKQDCrOmVQwuCBpY5pKvEJO3P6wSomL'
MERCHANT_UUID = '3b89f29b-2459-4bbd-bace-2f2e14df7aed'
payment = Client.payout(PAYMENT_KEY, MERCHANT_UUID)
API_BASE_URL = "https://api.cryptomus.com/v1"
CREATE_INVOICE_ENDPOINT = "/payment"

# BUTTONS
button_prolongate_daily = types.InlineKeyboardButton(text['button_daily'], callback_data='prolongate_daily')
button_prolongate_monthly = types.InlineKeyboardButton(text['button_monthly'], callback_data='prolongate_monthly')
button_prolongate_quarterly = types.InlineKeyboardButton(text['button_quarterly'], callback_data='prolongate_quarterly')
button_home_from_media = types.InlineKeyboardButton(text['button_home'], callback_data='home_from_media')
button_home = types.InlineKeyboardButton(text['button_home'], callback_data='home')
button_refresh = types.InlineKeyboardButton(text['button_refresh'], callback_data='home')
button_purchase = types.InlineKeyboardButton(text['button_buy'], callback_data='purchase')
button_manage = types.InlineKeyboardButton(text['button_manage'], callback_data='manage')
button_instructions = types.InlineKeyboardButton(text['button_instructions'], callback_data='instructions')
button_about = types.InlineKeyboardButton(text['button_about'], callback_data='about')
button_prolongate = types.InlineKeyboardButton(text['button_prolongate'], callback_data='prolongate')
button_quarterly = types.InlineKeyboardButton(text['button_quarterly'], callback_data='quarterly_subscription')
button_monthly = types.InlineKeyboardButton(text['button_monthly'], callback_data='monthly_subscription')
button_daily = types.InlineKeyboardButton(text['button_daily'], callback_data='daily_subscription')
button_trial = types.InlineKeyboardButton(text['button_trial'], callback_data='trial')
button_continue = types.InlineKeyboardButton(text['button_continue'], callback_data='home')
button_continue_change = types.InlineKeyboardButton(text['button_continue_change'], callback_data='continue_change')
button_Nuremberg = types.InlineKeyboardButton(text['nuremberg'], callback_data='nbg1')
button_Helsinki = types.InlineKeyboardButton(text['helsinki'], callback_data='hel1')
button_Moscow = types.InlineKeyboardButton(text['moscow'], callback_data='msk1')
button_Hillsboro = types.InlineKeyboardButton(text['hillsboro'], callback_data='hil')
button_Ashburn = types.InlineKeyboardButton(text['ashburn'], callback_data='ash')
button_Falkenstein = types.InlineKeyboardButton(text['falkenstein'], callback_data='fsn1')
button_crypto = types.InlineKeyboardButton(text['button_crypto'], callback_data='crypto_payment')
button_card =  types.InlineKeyboardButton(text['button_card'], callback_data='card_payment')
button_change_location = types.InlineKeyboardButton(text['button_change_location'], callback_data='change_location')
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
        'currency': 'RUB',
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

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message="Не удалось обработать платеж,"
                                                "повторите попытку еще раз.")


@bot.message_handler(commands=['start'])
def send_welcome(message):
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
            google_client = storage.Client(project='soy-envelope-400720')
            bucket = google_client.get_bucket('cfg-humanvpn')
            unique_id = str(uuid.uuid4()).replace("-", "")
            unique_id_short = unique_id[:16]
            blob = bucket.blob(f'{unique_id_short}')
            blob.upload_from_string('', content_type='application/json') 
            blob.cache_control = "no-cahe, max-age=0"
            blob.patch()
            json_url = str(blob.public_url)
            user_url = 'ssconf' + json_url[5:] + '#HumanVPN'
            dbu.update(cursor, 'UPDATE users_info_ru SET link = %s WHERE chat_id = %s', user_url, chat_id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(button_trial)
        bot.send_message(message.chat.id, text['start'], parse_mode='html', reply_markup=markup)
        mp.people_set(str(message.chat.id), {
            '$First_name': f'{message.from_user.first_name}',
            '$Last_name': f'{message.from_user.last_name}',
            '$Nickname': f'{username}',
        }, meta = {'$ignore_time': True, '$ip': 0})
        mp.track(str(message.chat.id), 'User started bot')
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
            link = dbu.fetch_one_for_query(cursor, 'SELECT link FROM users_info_ru WHERE chat_id = %s', chat_id)
            location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            location_to_display = locations[location]
            expiration_date = dbu.fetch_one_for_query(cursor, 'SELECT expiration_date FROM users_info_ru WHERE chat_id = %s', chat_id)
            username = call.from_user.username
            markup = types.InlineKeyboardMarkup(row_width=2)
            now = datetime.datetime.now()
            if expiration_date < now:
                status = 'Неактивно ❌'
                expiration_date = 'Истёк'
                annotation = 'Ваша подписка закончилась.. Всё лучшее подходит к концу. 💔\n\nНо конец старого - начало нового!\nПродлите подписку HumanVPN, нажав кнопку ниже ⬇️'
                markup.add(button_prolongate)
            else:
                status = 'Активно ✅'
                if server_ip is None:
                    status = '⚙️'
                    annotation = 'Сервер создаётся'
                    markup.add(button_prolongate, button_manage)
                elif server_ip in TRIAL_SERVER_IPS:
                    annotation = 'Пробный период HumanVPN'
                    markup.add(button_purchase, button_manage)
                else:
                    markup.add(button_prolongate, button_manage)
                    annotation = 'Полная версия HumanVPN'
            markup.add(button_instructions, button_about)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['home'].format(username=username, status=status, expiration=expiration_date,
                                                        location=location_to_display, users_link=link, annotation=annotation), parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User came home', {'Button name': f'{call.data}'})

        if call.data == 'home_from_media':
            chat_id = str(call.message.chat.id)
            server_ip = dbu.fetch_one_for_query(cursor, 'SELECT server_ip FROM users_info_ru WHERE chat_id = %s', chat_id)
            link = dbu.fetch_one_for_query(cursor, 'SELECT link FROM users_info_ru WHERE chat_id = %s', chat_id)
            location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            location_to_display = locations[location]
            expiration_date = dbu.fetch_one_for_query(cursor, 'SELECT expiration_date FROM users_info_ru WHERE chat_id = %s', chat_id)
            username = call.from_user.username
            markup = types.InlineKeyboardMarkup(row_width=2)
            now = datetime.datetime.now()
            if expiration_date < now:
                status = 'Неактивно ❌'
                expiration_date = 'Истёк'
                annotation = 'Оплатите подписку, чтобы получить доступ к HumanVPN'
                markup.add(button_prolongate, button_manage)
            else:
                status = 'Активно ✅'
                if server_ip is None:
                    status = '⚙️'
                    annotation = 'Сервер создаётся'
                    markup.add(button_prolongate, button_manage)
                elif server_ip in TRIAL_SERVER_IPS:
                    annotation = 'Пробный период HumanVPN'
                    markup.add(button_purchase, button_manage)
                else:
                    markup.add(button_prolongate, button_manage)
                    annotation = 'Полная версия HumanVPN'
            markup.add(button_instructions, button_about)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['home'].format(username=username, status=status, expiration=expiration_date,
                                                        location=location_to_display, users_link=link, annotation=annotation), parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User came home', {'Button name': f'{call.data}'})


    # Purchase logics --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

        if call.data == 'trial':
            markup = types.InlineKeyboardMarkup(row_width=1)
            hel = types.InlineKeyboardButton(text=text['helsinki'], callback_data='65.108.218.82')
            msk = types.InlineKeyboardButton(text=text['moscow'], callback_data='95.163.243.59')
            hil = types.InlineKeyboardButton(text=text['hillsboro'], callback_data='5.78.81.150')
            ash = types.InlineKeyboardButton(text=text['ashburn'], callback_data='5.161.81.114')
            fsn = types.InlineKeyboardButton(text=text['falkenstein'], callback_data='49.13.87.220')
            nbg = types.InlineKeyboardButton(text=text['nuremberg'], callback_data='128.140.34.117')
            markup.add(hel, msk, hil, ash, fsn, nbg)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['trial'], parse_mode='html', reply_markup=markup)

        if call.data == '65.108.218.82' or call.data == '95.163.243.59' or call.data == '5.78.81.150' or call.data == '5.161.81.114' or call.data == '49.13.87.220' or call.data == '128.140.34.117':
            chat_id = str(call.message.chat.id)
            location = trial_locations[call.data]
            dbu.update(cursor, 'UPDATE users_info_ru SET server_location = %s WHERE chat_id = %s', location, chat_id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_ios, button_android, button_macos, button_windows, button_linux, button_continue)
            trial_expiration_date = datetime.datetime.now() + datetime.timedelta(hours=24)
            date_to_display = trial_expiration_date.strftime('%H:%M:%S %d.%m.%Y')
            link = dbu.fetch_one_for_query(cursor, 'SELECT link FROM users_info_ru WHERE chat_id = %s', chat_id)
            location_to_display = locations[location]
            dbu.update(cursor, 'UPDATE users_info_ru SET expiration_date = %s, server_ip = %s, used_trial = 1 WHERE chat_id = %s', trial_expiration_date, call.data, chat_id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['continue'].format(date=date_to_display, location=location_to_display, link=link), parse_mode='html', reply_markup=markup)
        
        if call.data == 'continue':
            pass

        if call.data == 'purchase':
            chat_id = str(call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            used_trial = dbu.fetch_one_for_query(cursor, 'SELECT used_trial FROM users_info_ru WHERE chat_id=%s', chat_id)
            if used_trial == 1:
                markup.add(button_daily, button_monthly, button_quarterly, button_home)
            else:
                markup.add(button_trial, button_daily, button_monthly, button_quarterly, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['purchase'], parse_mode='html' ,reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered Purchase category', {'Button name': 'Purchase'})


        if call.data == 'monthly_subscription' or call.data == 'daily_subscription' or call.data == 'quarterly_subscription':
            chat_id = str(call.message.chat.id)
            days = {
                "quarterly_subscription": 90,
                "monthly_subscription": 30,
                "daily_subscription": 1
            }
            amount = {
                "quarterly_subscription": 999,
                "monthly_subscription": 399,
                "daily_subscription": 99
            }
            dbu.update(cursor, 'UPDATE users_info_ru SET duration_days = %s, amount = %s WHERE chat_id = %s', days[call.data], amount[call.data], chat_id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_Hillsboro, button_Ashburn, button_Nuremberg, button_Falkenstein, button_Helsinki, button_Moscow, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['location'], parse_mode='html' ,reply_markup=markup)
            mp.track(str(call.message.chat.id), f'User chose {call.data}', {'Button name': f'{call.data}'})

        if call.data == 'nbg1' or call.data == 'hel1' or call.data == 'fsn1' or call.data == 'msk1' or call.data == 'hil' or call.data == 'ash':
            chat_id = str(call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_card, button_crypto, button_home)
            dbu.update(cursor, 'UPDATE users_info_ru SET server_location = %s WHERE chat_id = %s',
                    call.data, call.message.chat.id)
            location = locations[call.data]
            days = dbu.fetch_one_for_query(cursor, 'SELECT duration_days FROM users_info_ru WHERE chat_id = %s', chat_id)
            duration = {
                1: "24 часа",
                30: "30 дней",
                90: "90 дней"
            }
            price = int(dbu.fetch_one_for_query(cursor, 'SELECT amount FROM users_info_ru WHERE chat_id = %s', chat_id))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=text['method'].format(location=location, days=duration[days], price=str(price)), parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), f'User chose {call.data}', {'Button name': f'{call.data}'})
                
        if call.data == 'crypto_payment':
            chat_id = str(call.message.chat.id)
            dbu.update(cursor, 'UPDATE users_info_ru SET payment_method = %s WHERE chat_id = %s',
                       call.data, call.message.chat.id)
            amount = str(dbu.fetch_one_for_query(cursor, 'SELECT amount FROM users_info_ru WHERE chat_id = %s', chat_id))
            duration = str(dbu.fetch_one_for_query(cursor, 'SELECT duration_days FROM users_info_ru WHERE chat_id = %s', chat_id))
            hosted_url = create_invoice(cursor, call.message.chat.id, duration, amount)
            button_link = types.InlineKeyboardButton(text='Оплатить счет', url=hosted_url)
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_home, button_link)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=text['invoice'].format(hosted_url=hosted_url), parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), f'User chose server {call.data}', {'Button name': f'{call.data}'})

        if call.data =='card_payment':
            chat_id = str(call.message.chat.id)
            dbu.update(cursor, 'UPDATE users_info_ru SET payment_method = %s WHERE chat_id = %s', call.data, chat_id) 
            amount = int(dbu.fetch_one_for_query(cursor, 'SELECT amount FROM users_info_ru WHERE chat_id = %s', chat_id))
            duration = str(dbu.fetch_one_for_query(cursor, 'SELECT duration_days FROM users_info_ru WHERE chat_id = %s', chat_id))
            bot.send_invoice(
                chat_id=chat_id,
                title=f'Оплата подписки HumanVPN {duration} день',
                description='Поддерживаем оплату Российскими картами МИР',
                invoice_payload='HUMAN VPN',
                provider_token=payment_token,
                currency='rub',
                prices=[LabeledPrice(label=f'Human VPN subscription', amount = amount * 100)]
            )

        # Manage my account logics

        if call.data == 'manage':
            chat_id = str(call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            location_to_display = locations[location]
            markup.add(button_change_location, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text['profile'].format(location=location_to_display), parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered Manage section', {'Button name': 'Manage'})

        if call.data == 'instructions':
            chat_id = str(call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_ios, button_android, button_macos, button_windows, button_linux, button_home_from_media)
            gif_code = dbu.fetch_one_for_query(cursor, 'SELECT gif_code FROM users_info_ru WHERE chat_id = %s', chat_id)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            if gif_code == None:
                emoji = bot.send_message(chat_id=call.message.chat.id, text='⏳')
                gif_code = bot.send_animation(chat_id=call.message.chat.id, animation=open('instruction.gif', 'rb'),
                                caption=text['instructions'], parse_mode='html', reply_markup=markup).animation.file_id
                bot.delete_message(chat_id=call.message.chat.id, message_id=emoji.message_id)
                dbu.update(cursor, 'UPDATE users_info_ru SET gif_code = %s WHERE chat_id = %s', gif_code, chat_id)
            else:
                bot.send_animation(chat_id=call.message.chat.id, animation=gif_code,
                                caption=text['instructions'], parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered instructions section', {'Button name': 'Instructions'})

        if call.data == 'prolongate':
            chat_id = str(call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_prolongate_daily, button_prolongate_monthly, button_prolongate_quarterly, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text['prolongate'], parse_mode='html', reply_markup=markup)
    
        if call.data == 'prolongate_daily' or call.data == 'prolongate_monthly' or call.data == 'prolongate_quarterly':
            chat_id = str(call.message.chat.id)
            days = {
                'prolongate_quarterly': 90,
                "prolongate_monthly": 30,
                "prolongate_daily": 1
            }
            amount = {
                "prolongate_quarterly": 999,
                "prolongate_monthly": 399,
                "prolongate_daily": 39
            }
            duration = {
                1: "24 часа",
                30: "30 дней",
                90: "90 дней"
            }
            dbu.update(cursor, 'UPDATE users_info_ru SET duration_days = %s, amount = %s WHERE chat_id = %s', days[call.data], amount[call.data], chat_id)
            price = int(dbu.fetch_one_for_query(cursor, 'SELECT amount FROM users_info_ru WHERE chat_id = %s', chat_id))
            location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_card, button_crypto, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=text['method'].format(location=locations[location], days=duration[days[call.data]], price=amount[call.data]), parse_mode='html', reply_markup=markup)
            

        if call.data == 'about':
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(button_instructions, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=text['about'], parse_mode='html', reply_markup=markup)
            mp.track(str(call.message.chat.id), 'User entered About section', {'Button name': 'About'})

        if call.data == 'change_location':
            chat_id = str(call.message.chat.id)
            location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_continue_change, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=text['change_location'].format(location=locations[location]), parse_mode='html', reply_markup=markup)
            
        if call.data == 'continue_change':
            local_button_Nuremberg = types.InlineKeyboardButton(text['nuremberg'], callback_data='local_nbg1')
            local_button_Helsinki = types.InlineKeyboardButton(text['helsinki'], callback_data='local_hel1')
            local_button_Moscow = types.InlineKeyboardButton(text['moscow'], callback_data='local_msk1')
            local_button_Hillsboro = types.InlineKeyboardButton(text['hillsboro'], callback_data='local_hil')
            local_button_Ashburn = types.InlineKeyboardButton(text['ashburn'], callback_data='local_ash')
            local_button_Falkenstein = types.InlineKeyboardButton(text['falkenstein'], callback_data='local_fsn1')
            chat_id = str(call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            mapping = {
                "hil": local_button_Hillsboro,
                "ash": local_button_Ashburn,
                "nbg1": local_button_Nuremberg,
                "fsn1": local_button_Falkenstein,
                "hel1": local_button_Helsinki,
                "msk1": local_button_Moscow
            }
            for label, button in mapping.items():
                if label != location:
                    markup.add(button)
            markup.add(button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text="Выберите новую локацию", reply_markup=markup)
            
        if call.data == 'local_hil' or call.data == 'local_ash' or call.data == 'local_nbg1' or call.data == 'local_fsn1' or call.data == 'local_hel1' or call.data == 'local_msk1':
            chat_id = str(call.message.chat.id)
            new_mapping = {
                "local_hil": "hil",
                "local_ash": "ash",
                "local_nbg1": "nbg1",
                "local_fsn1": "fsn1",
                "local_hel1": "hel1",
                "local_msk1": 'msk1',
            }
            server_ip = dbu.fetch_one_for_query(cursor, 'SELECT server_ip FROM users_info_ru WHERE chat_id = %s', chat_id)
            if server_ip in TRIAL_SERVER_IPS:
                dbu.update(cursor, 'UPDATE users_info_ru SET server_location = %s')
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(button_home)
            dbu.update(cursor, 'UPDATE users_info_ru SET server_location = %s WHERE chat_id = %s', new_mapping[call.data], chat_id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                    text=text['location_changed'].format(new_location=locations[new_mapping[call.data]]), parse_mode='html', reply_markup=markup)

 
    finally:
        connection.commit()
        connection.close()

bot.infinity_polling()
