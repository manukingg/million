import telebot
from telebot import types

bot = telebot.TeleBot('5826517455:AAEga_2bdw5IcwKpyPunegxYCQWulH5o9uM')
button_home = types.InlineKeyboardButton(text='Home', callback_data='home')
INSTRUCTION_TEXT = '''<b>Instructions:</b>'
<b>1</b>. Create your own server, by pressing <b>\'Purchase\'</b> button in the home menu. Perform the following steps and after that, you will get a special link.'

<em>Example: ss://Y2hhY...jCy5</em>'

<b>2.</b> To connect to your server, you need to download a free app <b>Outline*</b>.'

<b>3</b>. Copy your personal link and open <b>Outline</b> (it should automatically paste your link in). Press <b>\'Add server\'</b> and then <b>\'Connect\'.</b> (If the link did not pasted automatically, press <b>\'+\'</b> at the top-right corner and paste your link there).'

<b>4</b>. You\'re in! Feel free to use your internet to it\'s full potential.

<b>*</b>You can download <b>Outline</b> using menu below'''

@bot.message_handler(commands=['start'])
def send_welcome(message):
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

    if call.data == 'purchase':   
        pass

    if call.data == 'manage':
        pass

    if call.data == 'instructions':
        markup = types.InlineKeyboardMarkup(row_width=2)
        button_ios = types.InlineKeyboardButton(text='iOS', url='https://itunes.apple.com/us/app/outline-app/id1356177741')
        button_android = types.InlineKeyboardButton(text='Android', url='https://play.google.com/store/apps/details?id=org.outline.android.client')
        button_macos = types.InlineKeyboardButton(text='MacOS', url='https://itunes.apple.com/us/app/outline-app/id1356178125')
        button_windows = types.InlineKeyboardButton(text='Windows', url='https://s3.amazonaws.com/outline-releases/client/windows/stable/Outline-Client.exe')
        button_linux = types.InlineKeyboardButton(text='Linux', url='https://s3.amazonaws.com/outline-releases/client/linux/stable/Outline-Client.AppImage')
        markup.add(button_ios, button_android, button_macos, button_windows, button_linux, button_home)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=INSTRUCTION_TEXT, parse_mode='html', reply_markup=markup)

bot.infinity_polling()