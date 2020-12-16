# MADstatusbot
Telegram Statusbot for MAD with autoaction

![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)
![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)
![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)

## Installation Guide:

Clone the git repository.  
Create a virtual environment and install the requirements:  
```
apt install python-virtualenv

virtualenv -p python3 ~/MADstatusbot_env

cd ~/MADstatusbot

~/MADstatusbot_env/bin/pip install -r requirements.txt
```

Create a Telegram Bot.  
Copy config.json.example to config.json and do your configurations.  

Start the bot with:  
```
cd ~/MADstatusbot
~/MADstatusbot_env/bin/python madstatus.py
```

## Configuration: 

Set the following parameters:  

```
apitoken    : The apitoken form your bot  
madmin_url  : Multiple Instances to get the madmin status Page. Split multiple URL's by ','  
oktimeout   : Timeout after which /status shows the last data time  
language    : Language of user messages  
maintenance : don't do any action if true (default false)
actionwait  : Waiting time between checks  

tgcorrelation : Assign one chatid to one or multiple Oringins in MAD.  
                Only this chatid can query the Status and get Messages from the origins listet in box_origin.  
                If you set this to "all" you get status from all origins.  
                If you set this to "allmsg" you get messages from all origins.  
                "name" is only for your dokumentation and not used by the bot.  
		"verbose" ist optional. Default is False. If set to True this Account get  
			  more Messages like "MADURL ... startet for device xxxx"  
			  
             
action        : Set multiple timeouts and their todo (please have a look at the example below )  
                global  : this action is for origins with no special action entry  
                timeout : n minutes  
                todo    : todo the bot will do for you if the timeout is reached  
```

## Actions:
```
MSG      : Send a Message to all users who has an correlation to this origin.  
MADURL   : Send this URL to the madmin instance. The Bot will replace <ORIGIN> whit the origin name.
           Example:
           "MADURL:/restart_phone?origin=<ORIGIN>&adb=False"  -> reboot the origin
           "MADURL:/clear_game_data?origin=<ORIGIN>&adb=False"  -> clear PoGo game data
           "MADURL:/install_file?jobname=Reboot-Device&origin=<ORIGIN>&adb=False&type=JobType.CHAIN"  -> start Job reboot for the origin
SCR      : Execute a script. 
	   It is better to put complex code in one script.
	   !!! Beware: An invalid script can damage your whole instance. !!!
	   Example:
	   "SCR:/home/mad/utils/boxrestart.sh <ORIGIN>"
```

These Parameters are reloaded every minute:

oktimeout/actionwait/tgcorrelation/action/maintenance


Example:  
(please exchange everything with <....> by your values)  

```
{
        "apitoken": "<APITOKEN>",
        "madmin_url" : ["<USER>:<PASSWORD>@http://127.0.0.1:5050"],
        "oktimeout" : 20,
        "language" : "de",
        "maintenance" : false,
        "actionwait" : 60,
        "tgcorrelation": {
                        "<CHATID>": {
                                "name": "SuperAdmin",
				"verbose": true,
                                "box_origin": "all,allmsg"
                                },
                        "<CHATID>": {
                                "name": "<NAME>",
                                "box_origin": "all,<ORIGIN1>,<ORIGIN2>......."
                                }
                        },
        "action": {
                        "global": {
                                "60": "MSG"
                                },
                        "<ORIGIN1>": {
                                "25": "MADURL:/restart_phone?origin=<ORIGIN>&adb=False",
                                "35": "MSG"
                                },
                        "<ORIGIN2>": {
                                "40": "SCR:/home/mad/utils/boxrestart.sh <ORIGIN>",
				"60": "MSG"
                                }
                        }
}
```
## Commands for the bot:
```
/status          : shows an overview of the "update time" of the origins assigned to the users chatid.
/status <origin> : shows the "update time" of one origin.
```

## Changes

### 21. Sep 2020

Initial Version

### 1. Okt 2020

add verbose, allmsg and some new Messages

### 6. Okt 2020

new action SCR

### 16. Dez 2020

reload config every minute so some parameter changes are dynamic
Maintenancemode
