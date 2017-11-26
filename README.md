# Mycroft skill for Remember The Milk

This skill adds [Remember The Milk](https://www.rememberthemilk.com/) support to [Mycroft](https://mycroft.ai/).
The skill use Remember The Milk's [rest interface](https://www.rememberthemilk.com/services/api/).
This project is still in its early phases, two things to be aware of:

* An API key, secret and token is required, the skill cannot obtain these
* The only working command is adding items to lists, as shown below:

For example:

* "Hey Mycroft, add milk to my grocery list"
* "Hey Mycroft, add remember to call home to list Inbox "

The skill is using Remember The Milk ["smart add"](https://www.rememberthemilk.com/help/?ctx=basics.smartadd.whatis.) For example:

* "Hey Mycroft, add remember to call home tomorrow at 9 to list Inbox"

will add an item called "remember to call home" to the Remember The Milk's Inbox, and set the due date to tomorrow at 9.

# Configuration
To access your Remember The Milk account via the rest API, it is neccesary to apply for an API key at https://www.rememberthemilk.com/services/api/

That will give you an API key, and a shared secret. With these you must obtain an auth token, as described here:  https://www.rememberthemilk.com/services/api/

Automation of the above process is needed, but I still have to figure out the best way, given that Mycroft does not have a GUI.

The configuration to add to mycroft.conf looks like this.
```json
  "RtmSkill": {
    "api_key": "many_characters",
    "auth_token": "many_characters",
    "secret": "many_characters"
  }  
```


## Current state

Working features:
* Add an item to a list

Known issues:

TODO:
* A way to conviently obtain an auth token.
