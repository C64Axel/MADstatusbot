# MADstatusbot
Telegram Statusbot for MAD with autoaction

## Installation Guide:

```
pip install -r requirements.txt
```

Create a Telegram Bot.  
Copy config.json.example to config.json.  

Set the following parameters:

```
apitoken   : The apitoken form your bot  
madmin_url : Multiple Instances to get the madmin status Page. Split multiple URL's by ','  
oktimeout  : Timeout after which /status shows the last data time  
language   : Language of user messages  
actionwait : Waiting time between checks  

tgcorrelation : Assign one chatid to one or multiple Oringins in MAD.  
                Only this chatid can query the Status and get Messages from this origin.  
                If you set this to "all" you get the status from all origins.  
                "name" is only for your dokumentation and not used by the bot.  
             
action        : Set multiple timeouts and their todo (please have a look at the example below )  
                global  : this action is for origins with no special action entry  
                timeout : n minutes  
                todo    : todo the bot will do for you if the timeout is reached  
```

## Actions:
```
MSG      : Send a Message to all users who has an correlation to this origin.  
MADURL   : Send this URL to the madmin instance. Replace <ORIGIN> whit the origin name
           Example:
           "MADURL:/restart_phone?origin=<ORIGIN>&adb=False"  -> reboot the origin
           "MADURL:/clear_game_data?origin=<ORIGIN>&adb=False"  -> clear PoGo game data
           "MADURL:/install_file?jobname=Reboot-Device&origin=<ORIGIN>&adb=False&type=JobType.CHAIN"  -> start Job reboot for the origin
```

Example:  

```
{
        "apitoken": "<APITOKEN>",
        "madmin_url" : ["<USER>:<PASSWORD>@http://127.0.0.1:5050"],
        "oktimeout" : 20,
        "language" : "de",
        "actionwait" : 60,
        "tgcorrelation": {
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
                                "20": "MSG"
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
