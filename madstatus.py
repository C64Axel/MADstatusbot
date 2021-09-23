import telebot
import logging.handlers
import json
import time
import requests
import datetime
import subprocess
import shlex

from urllib3.exceptions import InsecureRequestWarning
from threading import Thread


##################
# Logging
logfilename = 'log/madstatusbot.log'
logger = logging.getLogger('madstatusbot')
logger.setLevel(logging.INFO)

logfile = logging.handlers.RotatingFileHandler(logfilename, maxBytes=5000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s|%(levelname)-8s|%(threadName)-15s|%(message)s')
logfile.setFormatter(formatter)
logger.addHandler(logfile)

telebot.logger.setLevel(logging.INFO)
telebot.logger.handlers = []
telebot.logger.addHandler(logfile)


##################
# enable middleware Handler
telebot.apihelper.ENABLE_MIDDLEWARE = True


##################
# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


##################
# read config,locales
f = open('config.json', "r")
config = json.load(f)
f.close()
msg_loc = json.load(open("locales/msg_" + config['language'].lower() + ".json"))


##################
# get bot information
bot = telebot.TeleBot(config['apitoken'])
try:
    botident = bot.get_me()
    botname = botident.username
    botcallname = botident.first_name
    botid = botident.id
except:
    logger.error("Error in Telegram. Can not find Botname and ID")
    quit()


##################
# Log all messages send to the bot
@bot.middleware_handler(update_types=['message'])
def log_message(bot_instance, message):
    logger.info("Message from ID:{}:{}:{}".format(message.from_user.id, message.from_user.username, message.text))


##################
#
def sendtelegram(chatid, msg):
    try:
        splitted_text = telebot.util.split_string(msg, 3000)
        for text in splitted_text:
            try:
                bot.send_message(chatid, text, parse_mode="markdown")
            except (ConnectionAbortedError, ConnectionResetError, ConnectionRefusedError):
                logger.warning("ConnectionError - Sending again after 5 seconds!!!")
                time.sleep(5)
                bot.send_message(chatid, text, parse_mode="markdown")
    except:
        logger.error("ERROR IN SENDING TELEGRAM MESSAGE TO {}".format(chatid))


##################
#
def reloadconfig():
    global config
    while True:
        try:
            f = open('config.json', "r")
            config_new = json.load(f)
            f.close()
            if config != config_new:
                config = config_new
                logger.info("Config reloaded")
        except:
            logger.error("ERROR IN CONFIG FILE")

        time.sleep(60)


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
            r = requests.get(madmin_url + '/get_status', auth=(madmin_up.split(":")[0], madmin_up.split(":")[1]), verify=False, timeout=1)
            if r.status_code == requests.codes.ok:
                logger.info("Getting status from {}".format(madmin_url))
                r = r.json()
                r.sort(key=get_name)
                status.append(r)
            else:
                logger.warning("Error getting status from {} Code: {}".format(madmin_url, r.status_code))
        except:
            logger.error("Timeout/Refused Error connecting to {}".format(madmin_url))

    return status


##################
# check for Actions
def check_action():

    #################
    # MSG
    def do_msg(origin, tgcorrelation, msg, check_verbose):
        for chatid in tgcorrelation:
            chat_devices = tgcorrelation[chatid]['box_origin']
            if ("allmsg" in chat_devices) or (origin in chat_devices):
                if not check_verbose or (check_verbose and tgcorrelation[chatid].get('verbose', False)):
                    logger.info("Send message for {} to {}".format(origin, chatid))
                    sendtelegram(chatid, msg)

    ##################
    # MADURL
    def do_madurl(origin, instance, url):
        madmin_up = instance.split("@")[0]
        madmin_url = instance.split("@")[1]

        url = url.replace("<ORIGIN>", origin)
        try:
            r = requests.get(madmin_url + url, auth=(madmin_up.split(":")[0], madmin_up.split(":")[1]), verify=False, timeout=1)
            if r.status_code != requests.codes.ok:
                logger.error("Error sending MADURL:{}:{}".format(madmin_url, r.status_code))
            return(r.status_code)
        except:
            pass

    ##################
    # CMD
    def do_cmd(origin, cmd):
        cmd = cmd.replace("<ORIGIN>", origin)
        p = subprocess.run(shlex.split(cmd))
        logger.info("CMD:{}".format(p))

    lasttodo = {}
    while True:

        maintenance = config.get('maintenance', None)

        if not maintenance:
            status = get_status()
            tgcorrelation = config['tgcorrelation']
            action = config['action']

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
                            logger.info("{} set status to normal".format(origin['name']))
                            do_msg(origin['name'], tgcorrelation, msg_loc["5"].format(origin['name']), False)
                            lasttodo[origin['name']] = 0

                        try:						# try to read last do index
                            last_todo = lasttodo[origin['name']]
                        except KeyError:				# restart: set last action for origin
                            last_todo = 0
                            try:
                                while diff >= int(list(action[boxname].keys())[last_todo + 1]):
                                    last_todo += 1
                            except IndexError:
                                pass
                            except:
                                raise
                            lasttodo[origin['name']] = last_todo

                        try:						# send message if not last action
                            timeout = int(list(action[boxname].keys())[last_todo])

                            if diff >= timeout:
                                todo = list(action[boxname].values())[last_todo].upper().split(":")[0]

                                logger.info("Action:{}:{:.2f}:{}".format(origin['name'], diff, todo))

                                if todo == "MSG":
                                    do_msg(origin['name'], tgcorrelation, msg_loc["2"].format(origin['name'], diff), False)
                                elif todo == "MADURL":
                                    url = list(action[boxname].values())[last_todo].split(":")[1]
                                    do_madurl(origin['name'], config['madmin_url'][instancekey], url)
                                    do_msg(origin['name'], tgcorrelation, msg_loc["4"].format(url, origin['name']), True)
                                elif todo == "SCR":
                                    cmd = list(action[boxname].values())[last_todo].split(":")[1]
                                    do_cmd(origin['name'], cmd)
                                    do_msg(origin['name'], tgcorrelation, msg_loc["6"].format(cmd, origin['name']), True)
                                else:
                                    logger.error("wrong action in {}".format(origin['name']))

                                lasttodo[origin['name']] += 1
                        except IndexError:
                            logger.info("Action:{}:{:.0f}:last action reached".format(origin['name'], diff))
        else:
            logger.warning("Maintenacemode is active")

        time.sleep(int(config['actionwait']))


##################
# Handle maintenance
@bot.message_handler(commands=['maint'])
def handle_maint(message):

    chat_id = message.from_user.id
    maintainer = config.get('maintainer', "")

    if str(chat_id) in maintainer:
        maintenance = config.get('maintenance', None)
        if maintenance:
            config['maintenance'] = False
        else:
            config['maintenance'] = True

        f = open('config.json', "w")
        json.dump(config, f, indent=4)
        f.close()

        logger.info("{} set maintenace mode to {}".format(chat_id, config.get('maintenance', None)))

        sendtelegram(chat_id, msg_loc["8"].format(config.get('maintenance', None)))


##################
# Handle status
@bot.message_handler(commands=['status'])
def handle_status(message):

    msg_out = msg_loc["1"]
    msg_out = msg_out + "``` ---------- -------- ---------------\n```"

    chat_id = message.from_user.id

    try:						# check correlation for catid
        chat_devices = config['tgcorrelation'][str(chat_id)]['box_origin']
    except:
        sendtelegram(chat_id, msg_loc["3"])
        return

    try:
        parameter = message.text.split(" ")[1]
        if parameter in config['tgcorrelation'][str(chat_id)]['box_origin']:
            chat_devices = parameter
        else:
            sendtelegram(chat_id, msg_loc["7"].format(parameter))
            return
    except:
        pass

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
                msg_out = msg_out + "``` {:10} {:>8} {:17}\n```".format(origin['name'], timediff, origin['rmname'])
    sendtelegram(chat_id, msg_out)

    if ("all" in chat_devices):
        msg_out = "```Bot Status:\n Thread loadconfig  is {}\n Thread checkaction is {}\n Maintenance        is {}```".format(t1.is_alive(),t2.is_alive(),config.get('maintenance', None))
        sendtelegram(chat_id, msg_out)

####################################################################

logger.info("Bot {} started".format(botname))

tmpmaintenance = False

t1 = Thread(name='loadconfig', target=reloadconfig, daemon=True, args=())
t1.start()

t2 = Thread(name='checkaction', target=check_action, daemon=True, args=())
t2.start()

try:
    bot.infinity_polling()
except KeyboardInterrupt:
    logger.info("Bot {} ended".format(botname))
