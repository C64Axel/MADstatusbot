import telebot
import logging
import sys
import json
import io
import time
import requests
import datetime
import threading
import shlex
import subprocess

from time import sleep
from urllib3.exceptions import InsecureRequestWarning
from threading import Thread,currentThread

##################
# enable middleware Handler
telebot.apihelper.ENABLE_MIDDLEWARE = True

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

##################
#read config,locales
with open ('config.json') as config_file:
	config = json.load(config_file)
msg_loc = json.load(open("locales/msg_" + config['language'].lower() + ".json"))


##################
# get bot information
bot = telebot.TeleBot(config['apitoken'],threaded=False)
try:
        botident = bot.get_me()
        botname = botident.username
        botcallname = botident.first_name
        botid = botident.id
except:
        log("Error in Telegram. Can not find Botname and ID")
        quit()


##################
# Logging
def my_excepthook(excType, excValue, traceback, logger=logging):
    logging.error("Logging an uncaught exception",
                 exc_info=(excType, excValue, traceback))
sys.excepthook = my_excepthook
threading.excepthook = my_excepthook

def log(msg):
        print (msg)
        logging.basicConfig(filename="log/" + botname + ".log", format="%(asctime)s|%(message)s", level=logging.INFO)
        logging.info(msg)

##################
# Log all messages send to the bot
@bot.middleware_handler(update_types=['message'])
def log_message(bot_instance, message):
	log("Message from ID:{}:{}:{}".format(message.from_user.id,message.from_user.username,message.text))


##################
#
def sendtelegram(chatid,msg):
	try:
		splitted_text = telebot.util.split_string(msg,3000)
		for text in splitted_text:
			bot.send_message(chatid,text,parse_mode="markdown")
	except:
		log("ERROR IN SENDING TELEGRAM MESSAGE TO {}".format(chatid))

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

		r = requests.get(madmin_url + '/get_status', auth=(madmin_up.split(":")[0], madmin_up.split(":")[1]), verify=False)
		if r.status_code == requests.codes.ok:
			r = r.json()
			r.sort(key=get_name)
			status.append(r)
		else:
			log("Error getting status from {}".format(madmin_url))

	return status


##################
# check for Actions
def check_action(wait,tgcorrelation,action):

	#################
	# MSG
	def MSG(origin,tgcorrelation,msg,check_verbose):
		for chatid in tgcorrelation:
			chat_devices = tgcorrelation[chatid]['box_origin']
			if ("allmsg" in chat_devices) or (origin in chat_devices):
				if not check_verbose or (check_verbose and (tgcorrelation[chatid].get('verbose','False').upper() == "TRUE")): 
					log("Send message for {} to {}".format(origin,chatid))
					sendtelegram(chatid,msg)

	##################
	# MADURL
	def MADURL(origin,instance,url):
		madmin_up = instance.split("@")[0]
		madmin_url = instance.split("@")[1]

		url = url.replace("<ORIGIN>",origin)
		r = requests.get(madmin_url + url, auth=(madmin_up.split(":")[0], madmin_up.split(":")[1]), verify=False)
		if r.status_code !=  requests.codes.ok:
			log("Error sending MADURL:{}:{}".format(madmin_url,r.status_code))
		return(r.status_code)

	##################
	# CMD
	def CMD(origin,cmd):
		cmd = cmd.replace("<ORIGIN>",origin)
		p = subprocess.run(shlex.split(cmd))
		log("CMD:{}".format(p))

	lasttodo = {}
	while True:

		status = get_status()

		for instancekey, instance in enumerate(status):
			for origin in instance:
				if origin['name'] in action:
					boxname = origin['name']
				else:
					boxname = "global"

				if boxname in action and origin['lastProtoDateTime']:
					diff = int((time.mktime(time.localtime()) - origin['lastProtoDateTime']))/60

											# reset if last action sucsessfull
					if diff < int(list(action[boxname].keys())[0]) and origin['name'] in lasttodo and lasttodo[origin['name']] > 0:
						log("{} set status to normal".format(origin['name']))
						MSG(origin['name'],tgcorrelation,msg_loc["5"].format(origin['name']),False)
						lasttodo[origin['name']] = 0

					try:						# try to read last todo index
						last_todo = lasttodo[origin['name']]
					except KeyError:				# restart: set last action for origin
						last_todo = 0
						try:
							while diff >= int(list(action[boxname].keys())[last_todo + 1]):
								last_todo += 1
						except IndexError:
							pass
						lasttodo[origin['name']] = last_todo

					try:						# send message if not last action
						timeout = int(list(action[boxname].keys())[last_todo])

						if diff >= timeout:
							todo = list(action[boxname].values())[last_todo].upper().split(":")[0]

							log("Action:{}:{:.2f}:{}".format(origin['name'],diff,todo))

							if todo == "MSG":
								MSG(origin['name'],tgcorrelation,msg_loc["2"].format(origin['name'],diff),False)
							elif todo == "MADURL":
								url = list(action[boxname].values())[last_todo].split(":")[1]
								MADURL(origin['name'],config['madmin_url'][instancekey],url)
								MSG(origin['name'],tgcorrelation,msg_loc["4"].format(url,origin['name']),True)
							elif todo == "SCR":
								cmd = list(action[boxname].values())[last_todo].split(":")[1]
								CMD(origin['name'],cmd)
								MSG(origin['name'],tgcorrelation,msg_loc["6"].format(cmd,origin['name']),True)
							else:
								log("wrong action in {}".format(origin['name']))

							lasttodo[origin['name']] += 1
					except IndexError:
						log("Action:{}:{:.0f}:last action reached".format(origin['name'],diff))
					except:
						raise

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
				if origin['lastProtoDateTime']:
					diff = int((time.mktime(time.localtime()) - origin['lastProtoDateTime']))
					if (diff / 60) < int(config['oktimeout']):
						timediff = "OK"
					else:
						timediff = str(datetime.timedelta(seconds=diff))
				else:
					timediff = "NONE"
				msg_out = msg_out + "``` {:10} {:>8} {:17}\n```".format(origin['name'],timediff,origin['rmname'])
	sendtelegram(chat_id,msg_out)

####################################################################

log("Bot {} started".format(botname))
t = Thread(target=check_action, args=(int(config['actionwait']),config['tgcorrelation'],config['action']))
t.setDaemon(True)
t.start()

while True:
	bot.polling(none_stop = False)

