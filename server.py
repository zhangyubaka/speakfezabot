#!/usr/bin/env python3
#coding=utf-8
__author__ = 'zhangyubaka'

import logging
import telebot
from sqlalchemy import Column, String, create_engine, Integer, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import re
import requests
import jieba.analyse
import random
import jieba.posseg as pseg
import entropy
import string
from collections import defaultdict
from random import randint
from time import sleep
import pdb
import datetime
import snownlp
from numpy.random import choice
import flask

DBNAME = "your database"

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (API_TOKEN)

API_TOKEN = '<api_token>'

WEBHOOK_HOST = '<ip/host where the bot is running>'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Path to the ssl private key


logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(API_TOKEN)

app = flask.Flask(__name__)

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return ''

@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().encode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_messages([update.message])
        return ''
    else:
        flask.abort(403)


engine = create_engine('sqlite:///' + DBNAME, echo=True)
DBSession = sessionmaker(bind=engine)

Base = declarative_base()


class MSG(Base):
    __tablename__ = 'MSG'

    id = Column(Integer, primary_key=True, autoincrement=True)
    Speaks = Column(String, autoincrement=True)
    sqlite_autoincrement=True


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello World!")


@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, "只是个什么都不会的 Bot 啦")


@bot.message_handler(commands=['status'])
def status(message):
    session = DBSession()
    bot.reply_to(message, repr(session.query(MSG.id).count()))
    session.close()


@bot.message_handler(commands=['analyze'])
def analyze(message):
    res = jieba.analyse.extract_tags(message.text.replace("/analyze", ""), topK=20, withWeight=True, allowPOS=())
    jiebamsg = ''.join(map(str, res))
    bot.reply_to(message, jiebamsg)

@bot.message_handler(commands=['zici'])
def choose(message):
    bot.send_chat_action(message.chat.id, 'typing')
    if len(message.text) > 5 and message.text != '':
        s = snownlp.SnowNLP(message.text)
        elements = ['吼啊', '你们不要想搞个什么大新闻']
        probablity = []
        probablity.append(s.sentiments)
        probablity.append(1 - s.sentiments)
        text = choice(elements, p=probablity)
        if text == '吼啊':
            moha = ['吼啊', '我是支持的。我就明确的告诉你。', '你一定要来问我,支持不支持。我们怎么能不支持?', '我就什么话也不说.这是坠吼的!']
            mohaw = [0.25, 0.25, 0.25, 0.25]
            text = choice(moha, p=mohaw)
            bot.send_message(message.chat.id, text)
        else:
            bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, '???')


@bot.message_handler(commands=['fspeak'])
def speak(message):
    session = DBSession()
    bot.send_chat_action(message.chat.id, 'typing')
    result = session.query(MSG.Speaks).all()
    result = [r[0] for r in result]
    try:
        bot.send_message(message.chat.id, session.query(MSG.Speaks).filter_by(id=randint(0, len(result))).one())
    except:
        bot.send_message(message.chat.id, session.query(MSG.Speaks).filter_by(id=randint(0, len(result))).first())
    session.close()


@bot.message_handler(commands=['entropy'])
def send_entropy(message):
    session = DBSession()
    now = datetime.datetime.now()
    bot.reply_to(message, '当前世界线:' + ' ' + repr(entropy.shannon_entropy(repr(session.query(MSG.Speaks).all()))))
    session.close()


@bot.message_handler(commands=['interest'])
def send_entropy(message):
    session = DBSession()
    bot.send_chat_action(message.chat.id, 'typing')
    result = session.query(MSG.Speaks).all()
    result = [r[0] for r in result]
    entropys = []
    for i in result:
        o = entropy.shannon_entropy(i)
        entropys.append(o)
    selected_one = random.choice(entropys)
    selected_index = entropys.index(selected_one)
    selected_text = result[selected_index]
    bot.reply_to(message, selected_text + '    ' + '该消息的熵值为' + '    ' + repr(selected_one))
    session.close()


@bot.message_handler(commands=['getentropy'])
def get_entropy(message):
    now = datetime.datetime.now()
    bot.reply_to(message, '该消息熵值为' + '    ' + repr(entropy.shannon_entropy(message.text + now.isoformat())))


@bot.message_handler(func=lambda message: message.reply_to_message)
def simple_reply(message):
    early = message.reply_to_message
    me = bot.get_me()
    if early.from_user.id == me.id:
        sspeak(message)
    savemsg(message)


def sspeak(message):
    session = DBSession()
    bot.send_chat_action(message.chat.id, 'typing')
    now = datetime.datetime.now()
    this_en = entropy.shannon_entropy(message.text + now.isoformat())
    result = session.query(MSG.Speaks).all()
    result = [r[0] for r in result]
    weights = []
    weight_only_list = []

    for msg in result:  #Get words list
        i = jieba.analyse.extract_tags(msg, topK=20, withWeight=False, allowPOS=())
        weights.append(i)

    this_top = jieba.analyse.extract_tags(message.text.replace("/sspeak", ""), topK=20, withWeight=False, allowPOS=()) #当前词重
    if this_top:
        a = [item for sublist in weights for item in sublist]  #Flatten this lists
        index = [i for i, j in enumerate(a) if j == this_top[0]]
        if len(index) < 1 and len(this_top) > 1:
            index = [i for i, j in enumerate(a) if j == this_top[1]]
        try:
            saying1 = result[index[0] + randint(-2, 2)]
            if saying1 != '。' and saying1 != '.' and saying1 != '，' and saying1 != ',':     #make sure no punchuation
                bot.reply_to(message, saying1)
            else:
                entropy_say(message)
        except IndexError:
            entropy_say(message)
    else:
        entropy_say(message)

    session.close()

def entropy_say(message):
    session = DBSession()
    now = datetime.datetime.now()
    this_en = entropy.shannon_entropy(message.text + now.isoformat())
    result = session.query(MSG.Speaks).all()
    result = [r[0] for r in result]
    entropys = []   #use entropy for who can't speak anymore
    for i in result:
        o = entropy.shannon_entropy(i)
        entropys.append(o)
    selected_one = min(range(len(entropys)), key=lambda i: abs(entropys[i]-this_en))
    selected_text = result[selected_one]
    bot.reply_to(message, selected_text)
    session.close()

@bot.message_handler(commands=['keyspeak'])
def keyspeak(message):
    session = DBSession()
    bot.send_chat_action(message.chat.id, 'typing')
    if message.text != '':
        message.text = message.text.replace('/keyspeak ', '')
        result = session.query(MSG.Speaks).all()
        result = [r[0] for r in result]
        if any(message.text in s for s in result):
            matching = [s for s in result if message.text in s]
            maxlen = len(matching)
            bot.send_message(message.chat.id, matching[0 + randint(0,maxlen)])
        else:
            bot.send_message(message.chat.id, '喵呜?')
    else:
        entropy_say(message)
    session.close()

@bot.message_handler(commands=['ensay'])
def ensay(message):
    try:
        entropy_say(message)
    except:
        send_entropy(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, 'pong/')

@bot.message_handler(commands=['entts', 'zhtts', 'jatts', 'yuetts', 'nltts', 'detts', 'frtts', 'datts', 'rutts', 'estts', 'ittts', 'eotts', 'eltts'])
def tts(message):
    headers = {'user-agent': 'Mozilla/5.0'}
    bot.send_chat_action(message.chat.id, 'record_audio')
    if len(message.text) > 4:
        text = message.text.replace("/", "")
        lang = text[0:text.find('tts')]
        text = text.replace("tts", "")
        text = text[text.find(" ") + 1:]
        try:
            url = 'http://translate.google.com/translate_tts?ie=UTF-8&total=1&idx=0&textlen=32&client=tw-ob&q=' + text + '&tl=' + lang
            voice = requests.get(url, headers=headers, stream=True)
            bot.send_voice(message.chat.id, voice.raw.read())
        except:
            bot.send_message(message.chat.id, '说不出话')
    else:
        bot.send_message(message.chat.id, '喵喵喵喵喵?')


@bot.message_handler(commands=['entop'])
def top(message):
    session = DBSession()
    bot.send_chat_action(message.chat.id, 'typing')
    result = session.query(MSG.Speaks).all()
    result = [r[0] for r in result]
    toplists = []
    for i in result:
        subtop = entropy.shannon_entropy(i)
        toplists.append(subtop)
    sort_top = sorted(toplists)
    try:
        numbers = [int(s) for s in message.text.split() if s.isdigit()]
        select_top = result[toplists.index(sort_top[-1 - numbers[0]])]
        bot.send_message(message.chat.id, select_top)
    except:
        top1 = toplists.index(sort_top[-1])
        top2 = toplists.index(sort_top[-2])
        top3 = toplists.index(sort_top[-3])
        top4 = toplists.index(sort_top[-4])
        top5 = toplists.index(sort_top[-5])
        text = result[top1] + '\n\n' + result[top2] + '\n\n' + result[top3] + '\n\n' + result[top4]  + '\n\n' + result[top5]
        try:
            splitted_text = telebot.util.split_string(text, 3000)
            for text in splitted_text:
                bot.send_message(message.chat.id, text)
        except:
            bot.send_message(message.chat.id, '说不出话.')
    session.close()


@bot.message_handler(func=lambda message: True)
def savemsg(message):
    session = DBSession()
    session.add(MSG(Speaks=message.text))
    session.commit()
    session.close()


bot.remove_webhook()


bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

app.run(host=WEBHOOK_LISTEN,
        port=WEBHOOK_PORT,
        ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
        debug=True)