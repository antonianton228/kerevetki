import os
import random
import telebot
import ydb

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))


driver = ydb.Driver(database=os.environ.get('database'), endpoint =os.environ.get('endpoint'), credentials=ydb.iam.MetadataUrlCredentials())
driver.wait(fail_fast=True, timeout=5)

# Wait for the driver to become active for requests.
driver.wait(fail_fast=True, timeout=5)
# Create the session pool instance to manage YDB sessions.
pool = ydb.SessionPool(driver)


def execute_query(session, a):
    f = session.transaction().execute(
        f'SELECT * from users where tgID = {a}',
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )[0].rows
    return f

def update_bd(session, a, t):
    print(a, t, f'''UPDATE users 
        set last_mes = "{t}"
        where tgID = {a}
        ''')
    f = session.transaction().execute(
        f'''UPDATE users 
        set last_mes = "{t}"
        where tgID = {a}
        ''',commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )
    return f

def create_new_user(session, a):
    print(a, f'''insert into users (id, last_mes, tgID) select MAX(id) + 1, "", {a} from users;
        ''')
    f = session.transaction().execute(
        f'''insert into users (id, last_mes, tgID) select MAX(id) + 1, "", {a} from users;
        ''',commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )

    return f  

def delete(session, a):
    f = session.transaction().execute(
        f'''
        DELETE FROM users WHERE tgID = {a}
        ''',commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )
    return f  

# ---------------- dialog params ----------------


def form_dict():
    d = {}
    iter = 0
    for i in range(32, 127):
        d[iter] = chr(i)
        iter = iter + 1
    return d


def encode_val(word):
    list_code = []
    lent = len(word)
    d = form_dict()

    for w in range(lent):
        for value in d:
            if word[w] == d[value]:
                list_code.append(value)
    return list_code


def comparator(value, key):
    len_key = len(key)
    dic = {}
    iter = 0
    full = 0

    for i in value:
        dic[full] = [i, key[iter]]
        full = full + 1
        iter = iter + 1
        if (iter >= len_key):
            iter = 0
    return dic


def full_encode(value, key):
    dic = comparator(value, key)
    lis = []
    d = form_dict()

    for v in dic:
        go = (dic[v][0] + dic[v][1]) % len(d)
        lis.append(go)
    return lis


def decode_val(list_in):
    list_code = []
    lent = len(list_in)
    d = form_dict()

    for i in range(lent):
        for value in d:
            if list_in[i] == value:
                list_code.append(d[value])
    return list_code



@bot.message_handler(commands=['start'])
def start_message(message):
    print(message)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("Усложнить пароль")
    markup.add(btn1)
    bot.send_message(message.chat.id,
                     text="Приветствую вас, я способен преобразовывать ваши запоминающиеся 'простые' пароли в более 'сложные' пароли, для этого необходимо лишь ввести ваш 'простой' пароль и слово-ключ, которые вы запомните. ",)
                     # reply_markup=markup)
    bot.send_message(message.chat.id,
                     text="Я буду незаменимым помощником в защите вашей конфиденциальной информации. С моей помощью вы сможете создавать надежные пароли, которые будут невозможны для злоумышленников и взломщиков. Ваша безопасность - моя первостепенная задача. ",
                     reply_markup=markup)
    bot.send_message(message.chat.id,
                     text="Для сохранения вашей конфиденциальности, я удаляю историю нашего чата через несколько минут после использования и нигде не сохраняю ваши пароли, чтобы никакой злоумышленник не мог узнать ваши пароли. ",
                     reply_markup=markup)
    bot.send_message(message.chat.id,
                     text="Для того, чтобы снова увидеть усложнённый пароль, просто напишите мне свой простой пароль и ключ ещё раз, тогда я выдам вам тот же пароль.")
    bot.send_message(message.chat.id, text="Что бы вы сейчас хотели сделать?", reply_markup=markup)


@bot.message_handler(content_types=['text'])
def func(message):
    users = pool.retry_operation_sync(lambda x: execute_query(x, message.chat.id))
    print(users)
    if (message.text == "Усложнить пароль"):
        bot.send_message(message.chat.id,
                         text="Напоминаю, что для создания простого пароля следует использовать строчные и заглавные латинские буквы, цифры и спецсимволы. Рекомендую использовать разные простые пароли и/или ключевые слова для каждого сервиса.")
        bot.send_message(message.chat.id, text="Введите ваш простой пароль:")
        pool.retry_operation_sync(lambda x: create_new_user(x, message.chat.id))


    elif (message.text == "Вернуться в главное меню"):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Усложнить пароль")
        markup.add(button1)
        bot.send_message(message.chat.id, text="Вы вернулись в главное меню", reply_markup=markup)
        pool.retry_operation_sync(lambda x: delete(x, message.chat.id))
    else:
        if users:
            users[0]['last_mes'] = users[0]['last_mes'].decode('utf-8')
            if str(users[0]['last_mes']) != '':
                word = users[0]['last_mes']
                key = message.text
                key_encoded = encode_val(key)
                value_encoded = encode_val(word)
                shifre = full_encode(value_encoded, key_encoded)
                bot.send_message(message.chat.id, text="Ваш пароль: ")
                bot.send_message(message.chat.id, text=''.join(decode_val(shifre)))

                pool.retry_operation_sync(lambda x: delete(x, message.chat.id))
            else:
                word = message.text
                bot.send_message(message.chat.id, text="Введите ваше слово-ключ (также латинскими буквами):")
                pool.retry_operation_sync(lambda x: update_bd(x, message.chat.id, word))

        else:
            bot.send_message(message.chat.id,
                             text="На такую комманду я пока что не запрограммирован... Возможно вы хотите что-то другое?")




# ---------------- local testing ----------------
if __name__ == '__main__':
    bot.infinity_polling()
