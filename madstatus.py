import telebot
import logging
import sys
import json
import io
import time
import requests
import datetime

from time import sleep
from urllib3.exceptions import InsecureRequestWarning
from threading import Thread

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

##################
# Logging
def my_excepthook(excType, excValue, traceback, logger=logging):
    logging.error("Logging an uncaught exception",
                 exc_info=(excType, excValue, traceback))
sys.excepthook = my_excepthook

def log(msg):
        print (msg)
        logging.basicConfig(filename="log/" + botname + ".log", format="%(asctime)s|%(message)s", level=logging.INFO)
        logging.info(msg)

##################
#read config
with open ('config.json') as config_file:
	config = json.load(config_file)

##################
#read locales
msg_loc = json.load(open("locales/msg_" + config['language'] + ".json"))

##################
# get bot information
bot = telebot.TeleBot(config['apitoken'])
try:
        botident = bot.get_me()
        botname = botident.username
        botcallname = botident.first_name
        botid = botident.id
except:
        log("Error in Telegram. Can not find Botname and ID")
        quit()

telebot.apihelper.ENABLE_MIDDLEWARE = True

##################
#
def sendtelegram(chatid,msg):
        try:
                splitted_text = telebot.util.split_string(msg,3000)
                for text in splitted_text:
                        bot.send_message(chatid,text,parse_mode="markdown")
        except:
                log ("ERROR IN SENDING TELEGRAM MESSAGE TO {}".format(chatid))

##################
# do some logging
@bot.middleware_handler(update_types=['message'])
def log_message(bot_instance, message):
	log("Message from ID:{}:{}:{}".format(message.from_user.id,message.from_user.username,message.text))

##################
# Get Status from Server
def get_status():

	##################
	# Sort by name
	def get_name(status):
		return status.get('name')

	status = []

	for url in config['madmin_url']:
		madmin_up = url.split("@")[0]
		madmin_url = url.split("@")[1]

		try:
			r = requests.get(madmin_url + '/get_status', auth=(madmin_up.split(":")[0], madmin_up.split(":")[1]), verify=False).json()
			r.sort(key=get_name)
			status.append(r)
		except:
			log("Error getting {}".format(madmin_url))

	return status

##################
# check for Actions
def check_action(wait,tgcorrelation,action):

	#################
	# MSG
	def MSG(origin,diff,tgcorrelation):
		for chatid in tgcorrelation:
			if origin in tgcorrelation[chatid]['box_origin']:
				msg_out = msg_loc["2"].format(origin,diff)
				log("Send message for {} to {}".format(origin,chatid))
				sendtelegram(chatid,msg_out)

	##################
	# MADREBOOT
	def MADREBOOT():
		pass

	lasttodo = {}
	while True:
		status = get_status()

		for instance in status:
			for origin in instance:
				if origin['name'] in action:
					boxname = origin['name']
				else:
					boxname = "global"

				if boxname in action:
					diff = int((time.mktime(time.localtime()) - origin['lastProtoDateTime']))/60

											# reset if last action sucsessfull
					if diff < int(list(action[boxname].keys())[0]):
						lasttodo[origin['name']] = 0

					try:						# try to read last todo index
						last_todo = lasttodo[origin['name']]
					except:						# restart: set last action for origin
						last_todo = 0
						try:
							while diff >= int(list(action[boxname].keys())[last_todo + 1]):
								last_todo += 1
						except:
							pass
						lasttodo[origin['name']] = last_todo

					try:						# send message if not last action
						timeout = int(list(action[boxname].keys())[last_todo])
						todo = list(action[boxname].values())[last_todo]


						if diff >= timeout:
							log("Action:{}:{:.2f}:{}".format(origin['name'],diff,todo))

							if todo.upper() == "MSG":
								MSG(origin['name'],diff,tgcorrelation)
							elif todo.upper() == "MADREBOOT":
								MADREBOOT()
							else:
								log("wrong action in {}".format(origin['name']))

							lasttodo[origin['name']] += 1
					except:
						log("Action:{}:{:.0f}:last action reached".format(origin['name'],diff))

		sleep(wait)
	

##################
# Handle status
@bot.message_handler(commands=['status'])
def handle_status(message):

	msg_out =           msg_loc["1"]
	msg_out = msg_out + "``` ---------- -------- ---------------\n```"

	chat_id=message.from_user.id

	try:
		chat_devices = message.text.split(" ")[1]
	except:
		try:
			chat_devices = config['tgcorrelation'][str(chat_id)]['box_origin']
		except:
			sendtelegram(chat_id,msg_loc["3"])
			return

	status = get_status()

	for instance in status:
		for origin in instance:
			if ("all" in chat_devices) or (origin['name'] in chat_devices):
				diff = int((time.mktime(time.localtime()) - origin['lastProtoDateTime']))
				if (diff / 60) < int(config['oktimeout']):
					timediff = "OK"
				else:
					timediff = str(datetime.timedelta(seconds=diff))
				msg_out = msg_out + "``` {:10} {:>8} {:17}\n```".format(origin['name'],timediff,origin['rmname'])
	sendtelegram(chat_id,msg_out)

####################################################################
log("Bot {} started".format(botname))

t = Thread(target=check_action, args=(int(config['actionwait']),config['tgcorrelation'],config['action']))
t.start()

bot.polling(none_stop=True)

