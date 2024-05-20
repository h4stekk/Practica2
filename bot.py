import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from ytmusicapi import YTMusic
from pytube import YouTube
import os
from moviepy.editor import *
import requests
from edit import BTOKEN

ytmusic = YTMusic()
connection = sqlite3.connect('bd.db', check_same_thread=False)
cursor = connection.cursor()
bot = telebot.TeleBot(BTOKEN, parse_mode=None)

@bot.message_handler(commands=['start'])
def welcome(message):
	mainkeyboard = InlineKeyboardMarkup()
	mainkeyboard.row_width = 2
	mainkeyboard.add(InlineKeyboardButton("Мої треки 🎵", callback_data="playlist"))
	bot.send_message(message.chat.id, "<b>Привіт, я бот, який допоможе завантажити будь-яку пісню в 2 кліки!</b>\n\n• Щоб знайти трек - введіть автора, назву трека або просто слова.\n• Зберігайте понадобивші пісні!\n• Обкладинки альбомів додаються!\n", reply_markup=mainkeyboard, parse_mode='html')
	cursor.execute(f"select userid from users where userid={message.chat.id}")
	data = cursor.fetchall()
	if not data:
		cursor.execute(f"INSERT INTO users(name,userid,username,cachehistory) VALUES('{message.chat.first_name}','{message.chat.id}','{message.chat.username}','none');")
		connection.commit()

@bot.message_handler(content_types=["text"])
def search(message):
	songsearch = InlineKeyboardMarkup()
	songsearch.row_width = 2
	result = ytmusic.search(query=message.text, filter='songs')
	cursor.execute(f"UPDATE users SET cachehistory = 'song={message.text}' WHERE userid = '{message.chat.id}'")
	connection.commit()
	cursor.execute(f"UPDATE users SET preceding = '{message.text}' WHERE userid = '{message.chat.id}'")
	connection.commit()
	if result:
		for x in range(0,5):
			songsearch.row(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})", callback_data=f"song={result[x]['videoId']}"))
		songsearch.row(InlineKeyboardButton(f"Назад", callback_data=f"main"))
		bot.send_message(message.chat.id, f"Пошук за запитом '{message.text}' ({len(result)}): ",reply_markup=songsearch, parse_mode='html')
	else:
		bot.send_message(message.chat.id, 'Нічого не знайдено :(', parse_mode='html')

def download(message, songid):
	yt = YouTube(f"https://www.youtube.com/watch?v={songid}")
	yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download(output_path="mp3")
	bot.send_message(message.chat.id, f'Завантаження трека - {yt.title}', parse_mode='html')
	convert_to_mp3(f"mp3/{yt.title}.mp4", f"mp3/{yt.title}.mp3", message, songid)

def convert_to_mp3(mp4_file, mp3_file, message, songid):
	video = VideoFileClip(mp4_file)
	audio = video.audio
	audio.write_audiofile(mp3_file)
	with open(f"{mp3_file}","rb") as song:
		audio=song.read()
	yt = YouTube(f"https://www.youtube.com/watch?v={songid}")
	bot.send_audio(message.chat.id, audio, title=yt.title, performer=yt.author)
	songsearch = InlineKeyboardMarkup()
	songsearch.row_width = 2
	cursor.execute(f"SELECT preceding FROM users WHERE userid ={message.chat.id}")
	data = cursor.fetchall()
	result = ytmusic.search(query=songid, filter='songs')
	if result:
		songsearch.add(InlineKeyboardButton(f"🎵 {result[0]['title']} - {result[0]['artists'][0]['name']} ({result[0]['duration']})", callback_data=f"song={result[0]['videoId']}"))
		if checkadd(message, result[0]['videoId']):
			songsearch.row(InlineKeyboardButton(f"👤 {result[0]['artists'][0]['name']}", callback_data=f"artists={result[0]['artists'][0]['name']}"), InlineKeyboardButton("Додати ➕", callback_data=f"sadd={result[0]['videoId']}"))
		else:
			songsearch.row(InlineKeyboardButton(f"👤 {result[0]['artists'][0]['name']}", callback_data=f"artists={result[0]['artists'][0]['name']}"), InlineKeyboardButton("Видалити ❌", callback_data=f"sdel={result[0]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"preceding"))
		bot.send_message(message.chat.id, f"Пошук за запитом '{data[0][0]}' ({len(result)}): ", reply_markup=songsearch, parse_mode='html')
	else:
		bot.send_message(message.chat.id, 'Нічого не знайдено :(', parse_mode='html')	

def preceding(message):
	songsearch = InlineKeyboardMarkup()
	songsearch.row_width = 2
	cursor.execute(f"SELECT preceding FROM users WHERE userid ={message.chat.id}")
	data = cursor.fetchall()
	result = ytmusic.search(query=data[0][0], filter='songs')
	if result:
		for x in range(0,5):
			songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})", callback_data=f"song={result[x]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"main"))
		bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f"Пошук за запитом '{data[0][0]}' ({len(result)}): ", reply_markup=songsearch,parse_mode='html')
	else:
		bot.send_message(message.chat.id, 'Нічого не знайдено :(', parse_mode='html')	

def playlist(message):
	playlistsong = InlineKeyboardMarkup()
	playlistsong.row_width = 3
	cursor.execute(f"SELECT page FROM users WHERE userid = {message.chat.id}")
	page = cursor.fetchall()
	cursor.execute(f"SELECT * FROM song WHERE userid = {message.chat.id}")
	dataplaylist = cursor.fetchall()
	for x in range(0,len(dataplaylist)):
		playlistsong.add(InlineKeyboardButton(f"🎵 {dataplaylist[x][1]} - {dataplaylist[x][4]}", callback_data=f"song={dataplaylist[x][3]}"))
	playlistsong.add(InlineKeyboardButton("Назад", callback_data=f"main"))
	bot.send_message(message.chat.id, 'Ваші збережені треки:', reply_markup=playlistsong, parse_mode='html')

def artists(message, artists):
	songsearch = InlineKeyboardMarkup()
	songsearch.row_width = 2
	result = ytmusic.search(query=artists, filter='songs')
	if result:
		for x in range(0,len(result)):
			if checkadd(message, result[x]['videoId']):
				songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})",callback_data=f"song={result[x]['videoId']}"), InlineKeyboardButton("Додати ➕", callback_data=f"add={result[x]['videoId']}"))
			else:
				songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})",callback_data=f"song={result[x]['videoId']}"), InlineKeyboardButton("Видалити ❌", callback_data=f"del={result[x]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"preceding"))
	bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f'Результати пошуку автора - "{artists}":', reply_markup=songsearch,parse_mode='html')
	cursor.execute(f"UPDATE users SET cachehistory = 'artists={artists}' WHERE userid = '{message.chat.id}'")
	connection.commit()

def delsong(message, idsong):
	cursor.execute(f"SELECT cachehistory FROM users WHERE userid ={message.chat.id}")
	dataupdate = cursor.fetchall()
	songsearch = InlineKeyboardMarkup()
	songsearch.row_width = 2	
	result = ytmusic.search(query=dataupdate[0][0].split('=')[1], filter='songs')
	cursor.execute(f"SELECT songid FROM song WHERE userid ={message.chat.id}")
	data = cursor.fetchall()
	for x in range(0,len(data)):
		if str(data[x][0]) == str(idsong):
			cursor.execute(f"DELETE FROM song WHERE songid='{idsong}' AND userid = '{message.chat.id}'")
			if dataupdate[0][0].split('=')[0] == 'song':
				for x in range(0,5):
					songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})", callback_data=f"song={result[x]['videoId']}"))
					if checkadd(message, result[x]['videoId']):
						songsearch.add(InlineKeyboardButton(f"👤 {result[x]['artists'][0]['name']}", callback_data=f"artists={result[x]['artists'][0]['name']}"), InlineKeyboardButton("Додати ➕", callback_data=f"add={result[x]['videoId']}"))
					else:
						songsearch.add(InlineKeyboardButton(f"👤 {result[x]['artists'][0]['name']}", callback_data=f"artists={result[x]['artists'][0]['name']}"), InlineKeyboardButton("Видалити ❌", callback_data=f"del={result[x]['videoId']}"))
				songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"main"))
				bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f"Пошук за запитом '{dataupdate[0][0].split('=')[1]}' ({len(result)}): ", reply_markup=songsearch,parse_mode='html')
			if dataupdate[0][0].split('=')[0] == 'artists':
				for x in range(0,10):
					if checkadd(message, result[x]['videoId']):
						songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})",callback_data="none"), InlineKeyboardButton("Додати ➕", callback_data=f"add={result[x]['videoId']}"))
					else:
						songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})",callback_data="none"), InlineKeyboardButton("Видалити ❌", callback_data=f"del={result[x]['videoId']}"))
				songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"preceding"))
				bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f'Результати пошуку автора - "{dataupdate[0][0].split("=")[1]}":', reply_markup=songsearch,parse_mode='html')

def add(message, idsong):
	cursor.execute(f"SELECT cachehistory FROM users WHERE userid ={message.chat.id}")
	dataupdate = cursor.fetchall()
	song = ytmusic.get_song(idsong)
	songsearch = InlineKeyboardMarkup()
	songsearch.row_width = 2
	result = ytmusic.search(query=dataupdate[0][0].split('=')[1], filter='songs')
	cursor.execute(f"SELECT songid FROM song WHERE userid ={message.chat.id}")
	data = cursor.fetchall()
	for x in range(0,len(data)):
		if str(data[x][0]) == str(idsong):
			return
	cursor.execute(f"INSERT INTO song(name,userid,songid,author) VALUES('{song['videoDetails']['title']}','{message.chat.id}','{idsong}','{song['videoDetails']['author']}');")
	connection.commit()
	if dataupdate[0][0].split('=')[0] == 'song':
		for x in range(0,5):
			songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})", callback_data=f"song={result[x]['videoId']}"))
			if checkadd(message, result[x]['videoId']):
				songsearch.add(InlineKeyboardButton(f"👤 {result[x]['artists'][0]['name']}", callback_data=f"artists={result[x]['artists'][0]['name']}"), InlineKeyboardButton("Додати ➕", callback_data=f"add={result[x]['videoId']}"))
			else:
				songsearch.add(InlineKeyboardButton(f"👤 {result[x]['artists'][0]['name']}", callback_data=f"artists={result[x]['artists'][0]['name']}"), InlineKeyboardButton("Видалити ❌", callback_data=f"del={result[x]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"main"))
		bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f"Пошук за запитом '{dataupdate[0][0].split('=')[1]}' ({len(result)}): ", reply_markup=songsearch,parse_mode='html')
	else:
		for x in range(0,10):
			if checkadd(message, result[x]['videoId']):
				songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})",callback_data="none"), InlineKeyboardButton("Додати ➕", callback_data=f"add={result[x]['videoId']}"))
			else:
				songsearch.add(InlineKeyboardButton(f"🎵 {result[x]['title']} - {result[x]['artists'][0]['name']} ({result[x]['duration']})",callback_data="none"), InlineKeyboardButton("Видалити ❌", callback_data=f"del={result[x]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"preceding"))
		bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=f'Результати пошуку автора - "{dataupdate[0][0].split("=")[1]}":', reply_markup=songsearch,parse_mode='html')

def checkadd(message, songid):
	cursor.execute(f"SELECT songid FROM song WHERE userid ={message.chat.id}")
	data = cursor.fetchall()
	for x in range(0,len(data)):
		if str(data[x][0]) == str(songid):
			return False
	return True

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
	if call.data.split("=")[0] == "artists":
		artists(call.message, call.data.split("=")[1])
	if call.data.split("=")[0] == "song":
		download(call.message, call.data.split("=")[1])
	if call.data.split("=")[0] == "add":
		add(call.message, call.data.split("=")[1])
	if call.data.split("=")[0] == "del":
		delsong(call.message, call.data.split("=")[1])
	if call.data == "preceding":
		preceding(call.message)
	if call.data == "main":
		req = requests.Session()
		req.get(f'https://api.telegram.org/bot{BTOKEN}/deletemessage?message_id={call.message.message_id}&chat_id={call.message.chat.id}')
		welcome(call.message)
	if call.data == "playlist":
		playlist(call.message)
	if call.data.split("=")[0] == "sadd":
		song = ytmusic.get_song(call.data.split("=")[1])
		songsearch = InlineKeyboardMarkup()
		songsearch.row_width = 2
		result = ytmusic.search(query=call.data.split("=")[1], filter='songs')
		cursor.execute(f"INSERT INTO song(name,userid,songid,author) VALUES('{song['videoDetails']['title']}','{call.message.chat.id}','{call.data.split('=')[1]}','{song['videoDetails']['author']}');")
		connection.commit()
		songsearch.add(InlineKeyboardButton(f"🎵 {result[0]['title']} - {result[0]['artists'][0]['name']} ({result[0]['duration']})", callback_data=f"song={result[0]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"👤 {result[0]['artists'][0]['name']}", callback_data=f"artists={result[0]['artists'][0]['name']}"), InlineKeyboardButton("Видалити ❌", callback_data=f"sdel={result[0]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"main"))
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Пошук за запитом '{result[0]['title']}' ({len(result)}): ", reply_markup=songsearch,parse_mode='html')
	if call.data.split("=")[0] == "sdel":
		cursor.execute(f"DELETE FROM song WHERE songid='{call.data.split('=')[1]}' AND userid = '{call.message.chat.id}'")
		connection.commit()
		song = ytmusic.get_song(call.data.split("=")[1])
		songsearch = InlineKeyboardMarkup()
		songsearch.row_width = 2
		result = ytmusic.search(query=call.data.split("=")[1], filter='songs')
		songsearch.add(InlineKeyboardButton(f"🎵 {result[0]['title']} - {result[0]['artists'][0]['name']} ({result[0]['duration']})", callback_data=f"song={result[0]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"👤 {result[0]['artists'][0]['name']}", callback_data=f"artists={result[0]['artists'][0]['name']}"), InlineKeyboardButton("Додати ➕", callback_data=f"sadd={result[0]['videoId']}"))
		songsearch.add(InlineKeyboardButton(f"Назад", callback_data=f"main"))
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Пошук за запитом '{result[0]['title']}' ({len(result)}): ", reply_markup=songsearch,parse_mode='html')


bot.infinity_polling()
