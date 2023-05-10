import telebot
from telebot import types
import http.client
import json
from datetime import datetime, timedelta
import db_utils as dbu
from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.images.domain import Image
from hcloud.locations.domain import Location
import time
import base64
import docker
import random
import string
import secrets
from dateutil.relativedelta import relativedelta
import subprocess
import threading

INSTRUCTION_TEXT = '''<b>Instructions:</b>
<b>1</b>. Create your own server, by pressing <b>\'Purchase\'</b> button in the home menu. Perform the following steps and after that, you will get a special link.

<em>Example: ss://Y2hhY...jCy5</em>

<b>2.</b> To connect to your server, you need to download a free app <b>Outline*</b>.'

<b>3</b>. Copy your personal link and open <b>Outline</b> (it should automatically paste your link in). Press <b>\'Add server\'</b> and then <b>\'Connect\'.</b> (If the link did not pasted automatically, press <b>\'+\'</b> at the top-right corner and paste your link there).

<b>4</b>. You\'re in! Feel free to use your internet to it\'s full potential.

<b>*</b>You can download <b>Outline</b> using the menu below'''

PURCHASE_TEXT = '''HumanVPN only has one available plan for now:
- 1 server.
- 5 TB traffic size.
- Unlimited users amount.

We are going to add more features, such as servers variety, different plans and payment methods. 
'''

#API's
bot = telebot.TeleBot('5826517455:AAEga_2bdw5IcwKpyPunegxYCQWulH5o9uM') #telebot API
API_TOKEN = 'NOSsbf93NQYRCQsb1kr3CoSLQTXRbvVraoNSJDPjIkdZYdZSZzRUOaTt8Zi4q4BS' #hetzner_API
#VARIABLES
button_home = types.InlineKeyboardButton(text='Home', callback_data='home')
alphabet = string.ascii_letters + string.digits

def expiration_checker(cursor, chat_id):
    order_date = dbu.fetch_one_for_query(cursor, 'SELECT order_date FROM users_info WHERE chat_id = %s', chat_id)
    expiration_date = (order_date + relativedelta(months=1)).strftime('%Y-%m-%d')
    
    


def invoice_json(invoice_id):
    conn = http.client.HTTPSConnection("api.commerce.coinbase.com")
    payload = ''
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-CC-Version': '2018-03-22',
    'X-CC-Api-Key': '8c24e775-d308-47e6-a4e1-60f924439adf'
    }
    conn.request("GET", f"/invoices/{invoice_id}", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    json_data = json.loads(data)
    return json_data

def create_server_hetzner(cursor, chat_id):
        SSH_KEY = 'Main'
        SERVER_LOCATION = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info WHERE chat_id = %s', chat_id)
        SERVER_NAME = f'{SERVER_LOCATION}-{int(time.time())}'
        SERVER_TYPE = 'cx11'
        SERVER_IMAGE = 'docker-ce'
        client = Client(token=API_TOKEN)
        ssh_key = client.ssh_keys.get_by_name(name=SSH_KEY)
        response = client.servers.create(
            name=SERVER_NAME,
            server_type=ServerType(name=SERVER_TYPE),
            image=Image(name=SERVER_IMAGE),
            location=Location(name=SERVER_LOCATION),
            ssh_keys=[ssh_key],
            )
        server = response.server
        new_server_ip = server.public_net.ipv4.ip
        new_server_id = server.id
        dbu.update(cursor, 'INSERT INTO servers (server_location, server_IP, user_amount, server_name, server_id) VALUES (%s, %s, %s, %s, %s)', SERVER_LOCATION, new_server_ip, 0, SERVER_NAME, new_server_id)
        while True:
            server = client.servers.get_by_id(server.id)
            if server.status == 'running':
                break
            time.sleep(5)
        time.sleep(15)
        result = subprocess.run(['ssh-keyscan', '-t', 'rsa', f'{new_server_ip}'], stdout=subprocess.PIPE)
        server_key = result.stdout.decode('utf-8')
        with open('/home/grigoriy/.ssh/known_hosts', 'a') as f:
            f.write(server_key)

def settle_user(chat_id):
    cursor = dbu.connection.cursor()
    server_ip = dbu.fetch_one_for_query(cursor, 'SELECT server_IP FROM servers WHERE server_location = (SELECT server_location FROM users_info WHERE chat_id = %s) AND user_amount < 4 ORDER BY user_amount DESC LIMIT 1', chat_id)
    print (server_ip)
    user_amount = dbu.fetch_one_for_query(cursor, 'SELECT user_amount FROM servers WHERE server_ip = %s', server_ip)
    print(user_amount)
    if user_amount == 3:
        thread = threading.Thread(target=create_server_hetzner, args=(cursor, chat_id))
        thread.start()
    client = docker.DockerClient(
        base_url=f'ssh://root@{server_ip}',
        use_ssh_client = True
        )
    method = 'chacha20-ietf-poly1305'
    password = ''.join(secrets.choice(alphabet) for i in range(10))
    server_port = str(random.randint(1000, 10000))
    client.containers.run(
        'shadowsocks/shadowsocks-libev',
        environment={'PASSWORD':password, 'METHOD':method},
        ports={8388:('0.0.0.0', server_port), '8388/udp':('0.0.0.0', server_port)},
        detach=True,
        restart_policy={'Name': 'always'})
    uri = f'{method}:{password}@{server_ip}:{server_port}'
    encoded_uri = 'ss://' + base64.b64encode(uri.encode('utf-8')).decode('utf-8')
    print(chat_id)
    current_invoice_id = dbu.fetch_one_for_query(cursor, 'SELECT current_invoice_id FROM users_info WHERE chat_id = %s', chat_id)
    print(current_invoice_id)
    order_date = invoice_json(current_invoice_id)['data']['updated_at']
    iso_date = datetime.strptime(order_date, '%Y-%m-%dT%H:%M:%SZ')
    mysql_order_date = iso_date.strftime('%Y-%m-%d')
    user_amount += 1
    dbu.update(cursor, 'UPDATE servers SET user_amount = %s WHERE server_IP = %s', user_amount, server_ip)
    dbu.update(cursor, 'UPDATE users_info SET order_date = %s, server_ip = %s, port_number = %s, password = %s, link = %s WHERE chat_id = %s', mysql_order_date, server_ip, server_port, password, encoded_uri, chat_id)
        
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cursor = dbu.connection.cursor()
    query = """SELECT chat_id FROM users_info WHERE chat_id = (%s)"""
    chat_id = message.chat.id
    username = message.from_user.username
    cursor.execute(query, (chat_id,))
    result = cursor.fetchone()
    if result is None:
        query = """INSERT INTO users_info (chat_id, user_nickname) VALUES (%s, %s)"""
        cursor.execute(query, (chat_id, username))
        dbu.connection.commit()
    markup = types.InlineKeyboardMarkup(row_width=2)
    button_purchase = types.InlineKeyboardButton(text='Purchase', callback_data='purchase')
    button_manage = types.InlineKeyboardButton(text='Manage my account', callback_data='manage')
    button_instructions = types.InlineKeyboardButton(text='Instructions', callback_data='instructions')
    button_about = types.InlineKeyboardButton('About..', callback_data='about')
    markup.add(button_purchase, button_manage, button_instructions, button_about)
    bot.send_message(message.chat.id, 'This is a alpha-version of a HumanVPN. The most secure VPN.', parse_mode='html', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data == 'home':
        markup = types.InlineKeyboardMarkup(row_width=2)
        button_purchase = types.InlineKeyboardButton(text='Purchase', callback_data='purchase')
        button_manage = types.InlineKeyboardButton(text='Manage my account', callback_data='manage')
        button_instructions = types.InlineKeyboardButton(text='Instructions', callback_data='instructions')
        button_about = types.InlineKeyboardButton('About..', callback_data='about')
        markup.add(button_purchase, button_manage, button_instructions, button_about)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='This is a alpha-version of a HumanVPN. The most secure VPN.', reply_markup=markup)

#Purchase logics --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    if call.data == 'purchase':
        markup = types.InlineKeyboardMarkup(row_width=1)
        button_buy = types.InlineKeyboardButton(text='USD 4.99 per month', callback_data='monthly_subscription')
        markup.add(button_buy, button_home)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=PURCHASE_TEXT, parse_mode='html', reply_markup=markup)
    
    if call.data =='monthly_subscription':
        markup = types.InlineKeyboardMarkup(row_width=2)
        button_crypto = types.InlineKeyboardButton(text='Crypto', callback_data='crypto_payment')
        markup.add(button_crypto, button_home)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Please, choose a payment method', reply_markup=markup)

    if call.data == 'crypto_payment':
        markup = types.InlineKeyboardMarkup(row_width=2)
        button_Nuremberg = types.InlineKeyboardButton(text='Nuremberg, Germany', callback_data='nbg1')
        button_Helsinki = types.InlineKeyboardButton(text='Helsinki, Finland', callback_data='hel1')
        button_Falkenstein = types.InlineKeyboardButton(text='Falkenstein, Germany', callback_data='fsn1')
        markup.add(button_Nuremberg, button_Helsinki, button_Falkenstein, button_home)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Choose a server location', reply_markup=markup)
    
    if call.data == 'nbg1' or call.data == 'hel1' or call.data == 'fsn1':
        cursor = dbu.connection.cursor()
        chat_id = str(call.message.chat.id)
        dbu.update(cursor, 'UPDATE users_info SET server_location = %s WHERE chat_id = %s', call.data, chat_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(button_home)
        conn = http.client.HTTPSConnection("api.commerce.coinbase.com")
        payload = json.dumps({
            "customer_email": "hatbotinok@mail.ru",
            "customer_name": "Grigorii",
            "memo": "Payment for HumanVPN",
            "local_price": {
                "amount": "4.99",
                "currency": "USD"
            }        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CC-Version': '2018-03-22',
            'X-CC-Api-Key': '8c24e775-d308-47e6-a4e1-60f924439adf'
        }
        conn.request("POST", "/invoices", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        json_data = json.loads(data)
        hosted_url = json_data['data']['hosted_url']
        invoice_status = json_data['data']['status']
        invoice_id = json_data['data']['id']
        dbu.update(cursor, 'UPDATE users_info SET invoice_status = %s, current_invoice_id = %s WHERE chat_id = %s', invoice_status, invoice_id, chat_id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Your invoice: {hosted_url}.\nYou have <b>one hour</b> to pay it.\nGo to <b>\'Manage my account\'</b> after making a payment, all needed information is stored there.\nAdditional link to your invoice is also in this section.', parse_mode='html', reply_markup=markup)

#Manage my account logics -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    if call.data == 'manage':
        conn = http.client.HTTPSConnection("api.commerce.coinbase.com")
        cursor = dbu.connection.cursor()
        chat_id = str(call.message.chat.id)
        current_invoice_id = dbu.fetch_one_for_query(cursor, 'SELECT current_invoice_id FROM users_info WHERE chat_id = %s', chat_id)
        payload = ''
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CC-Version': '2018-03-22'
        }
        conn.request("GET", f"/invoices/{current_invoice_id}")
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        json_data = json.loads(data)
        invoice_status = json_data['data']['status']
        print(invoice_status)
        if True: #invoice_status == 'PAID':
            server_ip = dbu.fetch_one_for_query(cursor, 'SELECT server_ip FROM users_info WHERE chat_id = %s', chat_id)   
            if server_ip == None:
                settle_user(chat_id)
            username = call.from_user.username
            order_date = dbu.fetch_one_for_query(cursor, 'SELECT order_date FROM users_info WHERE chat_id = %s', chat_id)
            ordered_untill = (order_date + relativedelta(months=1)).strftime('%d-%m-%Y')
            users_link = dbu.fetch_one_for_query(cursor, 'SELECT link FROM users_info WHERE chat_id = %s', chat_id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            button_change_location = types.InlineKeyboardButton(text='Change server location', callback_data='change_location')
            button_addinional_server = types.InlineKeyboardButton(text='Get additional server', callback_data='additional_server')
            button_instructions = types.InlineKeyboardButton(text='Instructions', callback_data='instructions')
            markup.add(button_change_location, button_addinional_server, button_instructions, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'User <b>{username}</b>\nTraffic left:\nPaid until: <b>{ordered_untill}</b>\nLink: <pre>{users_link}</pre> (tap to copy)', parse_mode='html', reply_markup=markup)
        elif invoice_status == None:
            pass
        else:
            current_invoice_id = dbu.fetch_one_for_query(cursor, 'SELECT current_invoice_id FROM users_info WHERE chat_id = %s', chat_id)
            status = invoice_json(current_invoice_id)['data']['status']
            hosted_url = invoice_json(current_invoice_id)['data']['hosted_url']
            if invoice_status != status:
                dbu.update(cursor, 'UPDATE users_info SET invoice_status = %s WHERE chat_id = %s', status, chat_id)
            markup = types.InlineKeyboardMarkup()
            button_invoice = types.InlineKeyboardButton(text='Your invoice', url=str(hosted_url))
            markup.add(button_invoice, button_home)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='You haven\'t paid your invoice. Please, proceed payment to see accout details', parse_mode='html', reply_markup=markup)
     
                        
    




    if call.data == 'instructions':
        markup = types.InlineKeyboardMarkup(row_width=2)
        button_ios = types.InlineKeyboardButton(text='iOS', url='https://itunes.apple.com/us/app/outline-app/id1356177741')
        button_android = types.InlineKeyboardButton(text='Android', url='https://play.google.com/store/apps/details?id=org.outline.android.client')
        button_macos = types.InlineKeyboardButton(text='MacOS', url='https://itunes.apple.com/us/app/outline-app/id1356178125')
        button_windows = types.InlineKeyboardButton(text='Windows', url='https://s3.amazonaws.com/outline-releases/client/windows/stable/Outline-Client.exe')
        button_linux = types.InlineKeyboardButton(text='Linux', url='https://s3.amazonaws.com/outline-releases/client/linux/stable/Outline-Client.AppImage')
        markup.add(button_ios, button_android, button_macos, button_windows, button_linux, button_home)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=INSTRUCTION_TEXT, parse_mode='html', reply_markup=markup)

#Second level logics----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

bot.infinity_polling()