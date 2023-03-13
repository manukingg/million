import telebot
import mysql.connector
import http.client
import json
from mysql.connector import Error
from telebot import types


#API's
bot = telebot.TeleBot('5826517455:AAEga_2bdw5IcwKpyPunegxYCQWulH5o9uM') #telebot API

button_home = types.InlineKeyboardButton(text='Home', callback_data='home')
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

db_name = 'users_database'
mysql_password = 'hatbot3401350'
start_counter = 0

def create_db_connection(host_name, user_name, user_password, auth_plug, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host = host_name,
            user = user_name,
            password = user_password,
            auth_plugin = auth_plug,
            database = db_name
        )
        print('MySQL database connection successful')
    except Error as err:
        print(f"Error: '{err}'")
    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query was successful")
    except Error as err:
        print("Error: '{err}'")

connection = create_db_connection('localhost', 'root', mysql_password, 'mysql_native_password', db_name) #connecting to mysql "users_database"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    cursor = connection.cursor()
    query = """SELECT chat_id FROM users_info WHERE chat_id = (%s)"""
    chat_id = message.chat.id
    username = message.from_user.username
    cursor.execute(query, (chat_id,))
    result = cursor.fetchone()
    if result is None:
        query = """INSERT INTO users_info (chat_id, user_nickname) VALUES (%s, %s)"""
        cursor.execute(query, (chat_id, username))
        connection.commit()
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
        button_Nuremberg = types.InlineKeyboardButton(text='Nuremberg, Germany', callback_data='Nuremberg')
        markup.add(button_Nuremberg, button_home)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Choose a server location', reply_markup=markup)
    
    if call.data == 'Nuremberg':
        cursor = connection.cursor()
        chat_id = str(call.message.chat.id)
        query = 'UPDATE users_info SET server_location = %s WHERE chat_id = %s'
        cursor.execute(query, (call.data, chat_id,))
        connection.commit()
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
            }
        })
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
        query = 'UPDATE users_info SET invoice_status = %s, current_invoice_id = %s WHERE chat_id = %s'
        cursor.execute(query, (invoice_status, invoice_id, chat_id))
        connection.commit()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Your invoice: {hosted_url}.\nYou have <b>one hour</b> to pay it.\nGo to <b>\'Manage my account\'</b> after making a payment, all needed information is stored there.\nAdditional link to your invoice is also in this section.', parse_mode='html', reply_markup=markup)

#Purchase logics --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#Manage my account logics -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    if call.data == 'manage':
        conn = http.client.HTTPSConnection("api.commerce.coinbase.com")
        chat_id = str(call.message.chat.id)
        cursor = connection.cursor()
        query = 'SELECT invoice_status FROM users_info WHERE chat_id = %s'
        cursor.execute(query, (chat_id,))
        invoice_status = cursor.fetchone()[0]
        print(invoice_status)
        if invoice_status == 'PAYED':
            markup = types.InlineKeyboardMarkup(row_width=2)
            button_change_location = types.InlineKeyboardButton(text='Change server location', callback_data='change_location')
            button_addinional_server = types.InlineKeyboardButton(text='Get additional server', callback_data='additional_server')
            button_instructions = types.InlineKeyboardButton(text='Instructions', callback_data='instructions')
            markup.add(button_change_location, button_addinional_server, button_instructions, button_home)
            username = call.from_user.username
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'User <b>{username}</b>\nTraffic left:\nPayed until\nLink:', parse_mode='html', reply_markup=markup)
        elif invoice_status == None:
            pass
        else:
            query = 'SELECT current_invoice_id FROM users_info WHERE chat_id = %s'
            cursor.execute(query, (chat_id,))
            result = cursor.fetchone()
            current_invoice_id = result[0]
            payload = ''
            headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CC-Version': '2018-03-22',
            'X-CC-Api-Key': '8c24e775-d308-47e6-a4e1-60f924439adf'
            }
            conn.request("GET", f"/invoices/{current_invoice_id}", payload, headers)
            res = conn.getresponse()
            data = res.read().decode("utf-8")
            json_data = json.loads(data)
            status = json_data['data']['status']
            hosted_url = json_data['data']['hosted_url']
            if invoice_status != status:
                query = 'UPDATE users_info SET invoice_status = %s WHERE chat_id = %s'
                cursor.execute(query, (status, chat_id,))
                connection.commit()
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