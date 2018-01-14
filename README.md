## Skill The Cows Lists
Interact with "Remember The Milk" list and task management ecosystem.

## Description
This skill adds [Remember The Milk](https://www.rememberthemilk.com/) support to [Mycroft](https://mycroft.ai/).
The skill use Remember The Milk's [rest interface](https://www.rememberthemilk.com/services/api/).
The purpose if the skill is to allow simple for operations suited for a voice interface. Currently it is possible to add tasks to a list, and to undo an operation. An authentication flow is supported, and must be executed before other operations can be done, see section [Configuration](##Configuration)

#### Add a task
For example:
* "Hey Mycroft, add milk to my grocery list"
* "Hey Mycroft, add remember to call home to list Inbox "

The skill is using Remember The Milk ["smart add"](https://www.rememberthemilk.com/help/?ctx=basics.smartadd.whatis.) For example:

* "Hey Mycroft, add remember to call home tomorrow at 9 to list Inbox"

will add an item called "remember to call home" to the Remember The Milk's Inbox, and set the due date to tomorrow at 9.

The skill will try to recognize mispronounced list names, for example:
* You: "Hey Mycroft, add task to my bin box list"
* Mycroft: "I can't find a list called bin box, do you want to add the task to inbox instead?
* You: "Hey Mycroft, yes"
* Mycroft: "Item task was added to list inbox"

You must answer yes or no within 2 minutes, or Mycroft will forget  the context, and will not add the task to the list.

Be careful about using the word 'list' when you name the lists in Remember The Milk. For instance, the skill can handle a list called 'grocery' OR a list called 'grocery list', but if you have BOTH, the skill will only find the 'grocery list'.

#### Undo
You can undo the last operation, within 2 minutes, for example:
* You: "Hey Mycroft, add task to list Inbox"
* Mycroft: "Item task was added to list inbox"
* You: "Hey Mycroft, undo"
* Mycroft: "I have removed task from list inbox again"

#### Read list
Read the tasks on a list:
* You: "Hey Mycroft, read list inbox"
* Mycroft: "List inbox has 2 tasks on it, call home, go fishing"

The skill will try to find the best match among your lists, if you refer to a list that foes not exist.

#### Is item on list
Find an item on a list:
* You: "Hey Mycroft, find milk on my grocery list"
* Mycroft: "I found milk on list grocery"

The skill will try to match both list and task, like this:
* You: "Hey Mycroft, find blink on my grocery store list"
* Mycroft: "I cant find a list called grocery store, I am using the list grocery instead"
* Mycroft: "I did not find blink, but I did find milk on list grocery"


## Configuration
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
