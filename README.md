## Skill The Cows Lists
Mycroft skill for "Remember The Milk"

## Description
This skill adds [Remember The Milk](https://www.rememberthemilk.com/) support to [Mycroft](https://mycroft.ai/).
The skill use Remember The Milk's [rest interface](https://www.rememberthemilk.com/services/api/).
This project is still in its early phases. Authentication and add item to list are currently the only commands.

For example:

* "Hey Mycroft, add milk to my grocery list"
* "Hey Mycroft, add remember to call home to list Inbox "

The skill is using Remember The Milk ["smart add"](https://www.rememberthemilk.com/help/?ctx=basics.smartadd.whatis.) For example:

* "Hey Mycroft, add remember to call home tomorrow at 9 to list Inbox"

will add an item called "remember to call home" to the Remember The Milk's Inbox, and set the due date to tomorrow at 9.

### Configuration
To access your Remember The Milk account via the rest API, it is neccesary to apply for an API key at
[https://www.rememberthemilk.com/services/api/](https://www.rememberthemilk.com/services/api/). Click on the "Apply for an API key" button, and fill in the information. You will get a mail from remember the milk containing:
* An api key
* A shared secret

Head over to [https://home.mycroft.ai](https://home.mycroft.ai), log on, and go to "Skills" section. If you have installed
the cows list skill, it is possible enter the api key and the secret from remember the milk in the configuration section "Skill the cows lists".

Then say "Hey Mycroft, authenticate with remember the milk"

Mycroft will send you a mail containing an authentication link, pointing to remember the milk. Click on the link, and
authenticate Mycroft as described there.

After authentication with remember the milk, and only then, say:

"Hey Mycroft, get a token for remember the milk"

Now, Mycroft is ready to add items to your lists.

As an alternative, if you don't want to store your api key and secret at home.mycroft.ai, you can instead add the following
to mycroft.conf:

```json
  "TheCowsLists": {
    "api_key": "many_characters",
    "secret": "many_characters"
  }  
```

#### If your token expire or become invalid
On rare occasions the token may expire or become invalid. In that case you must repeat the steps above.
You still have to click on the authentication link in the mail, even though the page you are redirected to will say
that you are already authenticated (you may have to log in, if your browser is not already logged in to remember
the milk).

## Examples
* ""Hey Mycroft, add milk to my grocery list""
* ""Hey Mycroft, add remember to call home tomorrow at 9 to list Inbox""

## Credits
Carsten Agerskov (https://github.com/CarstenAgerskov)
