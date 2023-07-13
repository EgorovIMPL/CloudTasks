import os
import json
import requests
import datetime
import math
import telebot
import xml.etree.ElementTree as XmlElementTree
import httplib2
import uuid

FUNC_RESPONSE = {
    'statusCode': 200,
    'body': ''
}

YANDEX_ASR_HOST = 'asr.yandex.net'
YANDEX_ASR_PATH = '/asr_xml'
CHUNK_SIZE = 1024 ** 2

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def read_chunks(chunk_size, bytes):
    while True:
        chunk = bytes[:chunk_size]
        bytes = bytes[chunk_size:]

        yield chunk

        if not bytes:
            break


def speech_to_text(filename=None, bytes=None, request_id=uuid.uuid4().hex, topic='notes', lang='ru-RU',
                   key=os.environ.get("YANDEX_API_KEY")):
    # Если передан файл
    if filename:
        with open(filename, 'br') as file:
            bytes = file.read()
    if not bytes:
        raise Exception('Neither file name nor bytes provided.')
    
    # Формирование тела запроса к Yandex API
    url = YANDEX_ASR_PATH + '?uuid=%s&key=%s&topic=%s&lang=%s' % (
        request_id,
        key,
        topic,
        lang
    )

    # Считывание блока байтов
    chunks = read_chunks(CHUNK_SIZE, bytes)

    # Установление соединения и формирование запроса 
    connection = httplib2.HTTPConnectionWithTimeout(YANDEX_ASR_HOST)

    connection.connect()
    connection.putrequest('POST', url)
    connection.putheader('Transfer-Encoding', 'chunked')
    connection.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000')
    connection.endheaders()

    # Отправка байтов блоками
    for chunk in chunks:
        connection.send(('%s\r\n' % hex(len(chunk))[2:]).encode())
        connection.send(chunk)
        connection.send('\r\n'.encode())

    connection.send('0\r\n\r\n'.encode())
    response = connection.getresponse()

    # Обработка ответа сервера
    if response.code == 200:
        response_text = response.read()
        xml = XmlElementTree.fromstring(response_text)

        if int(xml.attrib['success']) == 1:
            max_confidence = - float("inf")
            text = ''

            for child in xml:
                if float(child.attrib['confidence']) > max_confidence:
                    text = child.text
                    max_confidence = float(child.attrib['confidence'])

            if max_confidence != - float("inf"):
                return text



def send_message(text, message):
    message_id = message['message_id']
    chat_id = message['chat']['id']
    reply_message = {'chat_id': chat_id,
                     'text': text,
                     'reply_to_message_id': message_id}
    requests.post(url=f'{TELEGRAM_API_URL}/sendMessage', json=reply_message)

def prepare_send(response,message_in):
    data = response.json()
    city = data["city"]["name"]
    cur_temp = data["list"][0]["main"]["temp"]
    feels_like = data["list"][0]["main"]["feels_like"]
    humidity = data["list"][0]["main"]["humidity"]
    pressure = data["list"][0]["main"]["pressure"]
    wind = data["list"][0]["wind"]["speed"]
    visibility = data["list"][0]["visibility"]
    sunrise = data['city']['sunrise']
    sunrise_timestamp = datetime.datetime.fromtimestamp(sunrise)
    sunset = data['city']['sunset']
    sunset_timestamp = datetime.datetime.fromtimestamp(sunset)
    description = data["list"][0]['weather'][0]['description']
    send_message(f"{description.title()}\nТемпература: {cur_temp}°C, ощущается как {feels_like}℃\nВлажность: {humidity}%\nДавление: {math.ceil(pressure/1.333)} мм.рт.ст\nВетер: {wind} м/с \nВидимость: {visibility}м\nВосход солнца: {sunrise_timestamp}\nЗакат солнца: {sunset_timestamp}\n", message_in)
        

def handler(event, context):
    
    if TELEGRAM_BOT_TOKEN is None:
        return FUNC_RESPONSE

    update = json.loads(event['body'])

    if 'message' not in update:
        return FUNC_RESPONSE

    message_in = update['message']

    if 'text' not in message_in and 'voice' not in message_in and 'location' not in message_in:
        send_message('Я не могу ответить на такой тип сообщения.\nНо могу ответить на:\n- Текстовое сообщение с названием населенного пункта.\n- Голосовое сообщение с названием населенного пункта.\n- Сообщение с точкой на карте.', message_in)
        return FUNC_RESPONSE

    try:
        weather_token = os.environ.get('WEATHER_TOKEN')
        response = requests.get(url="https://api.openweathermap.org/data/2.5/forecast")
        if 'location' in message_in:
            try:
                response = requests.get(url=f"https://api.openweathermap.org/data/2.5/forecast?lat={message_in['location']['latitude']}&lon={message_in['location']['longitude']}&lang=ru&units=metric&appid={weather_token}")
                prepare_send(response, message_in)
            except:
                send_message("Я не знаю какая погода в этом месте.", message_in)
                return FUNC_RESPONSE
        if 'text' in message_in  and (message_in["text"] == "/start" or message_in["text"] == "/help"):
            send_message('Я сообщу вам о погоде в том месте, которое сообщите мне.\nЯ могу ответить на:\n- Текстовое сообщение с названием населенного пункта.\n- Голосовое сообщение с названием населенного пункта.\n- Сообщение с точкой на карте.', message_in)
            return FUNC_RESPONSE
        if 'text' in message_in:
            try:
                response = requests.get(url=f"https://api.openweathermap.org/data/2.5/forecast?q={message_in['text']}&lang=ru&units=metric&appid={weather_token}")
                prepare_send(response, message_in)
            except:
                send_message(f"Я не нашел населенный пункт {message_in['text']}.", message_in)
                return FUNC_RESPONSE
        if 'voice' in message_in:
            file_info = bot.get_file(message_in['voice']['file_id'])
            voice_file = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}")
            text = speech_to_text(bytes=voice_file.content)
            try:
                response = requests.get(url=f"https://api.openweathermap.org/data/2.5/forecast?q={text}&lang=ru&units=metric&appid={weather_token}")
                prepare_send(response, message_in)
            except:
                send_message(f"Я не нашел населенный пункт {text}.", message_in)
            return FUNC_RESPONSE
        return FUNC_RESPONSE
    except:
        return FUNC_RESPONSE
    
    

    