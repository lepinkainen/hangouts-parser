#!/usr/bin/python3
import json
import sys
import os

OUTDIR = os.path.join(sys.path[0], 'logs/')
if not os.path.exists(OUTDIR):
    os.mkdir(OUTDIR)

print("Parsing data...")
DATA = json.loads(open("Hangouts.json").read())
print("Done")

# [u'continuation_end_timestamp', u'conversation_state']

DATA = DATA['conversation_state']

# list of conversations

# [u'conversation_id', u'response_header', u'conversation_state']

# conversation_id = just the ID, no use
# response_header = useless header data
# conversation_state -> more stuff

# [u'conversation_id', u'conversation', u'event']
# conversation_id = just the ID, no use
# conversation = ?
# event = list of actual messages??

# conversation:
# [u'otr_toggle', u'fork_on_external_invite', u'force_history_state', u'type', u'participant_data', u'self_conversation_state', u'current_participant', u'has_active_hangout', u'group_link_sharing_status', u'otr_status', u'network_type', u'read_state', u'id']
# [u'otr_toggle', u'fork_on_external_invite', u'name', u'type', u'participant_data', u'id', u'current_participant', u'has_active_hangout', u'group_link_sharing_status', u'otr_status', u'network_type', u'read_state', u'self_conversation_state', u'force_history_state']

# type = STICKY_ONE_TO_ONE|GROUP

# participant_data = people in chat

users = {}


def resolve_user(gaia_id):

    if gaia_id in users:
        return users[gaia_id]

    apikey = os.environ["GPLUS_APIKEY"]
    api_url = "https://www.googleapis.com/plus/v1/people/%s?key=%s"

    if not apikey:
        print("API key not found, define GPLUS_APIKEY environment variable")
        sys.exit(1)

    import requests

    data = requests.get(api_url % (gaia_id, apikey))
    json = data.json()

    if data.status_code == 200:
        # cache
        users[gaia_id] = json['displayName']

        return users[gaia_id]
    elif data.status_code == 404:
        return "USER NOT FOUND: %s" % gaia_id
    else:
        return "UNKNOWN: %s" % gaia_id

class Chat(object):
    """A single hangouts (group) chat"""

    def __init__(self, conversation_id, participants=None, chat_type="Unknown", name=None):
        self.conversation_id = conversation_id
        self.events = []
        self.name = name
        self.users = []
        self.participants = participants or []
        for participant in self.participants:
            self.users.append(User(participant))

        if name != None:
            self.type = "NAMED_GROUP"
        else:
            self.type = chat_type

        if self.name:
            self.filename = self.name
        else:
            self.filename = self.conversation_id

    def get_user(self, user_id):
        """Get user by id"""
        for user in self.users:
            if user.chat_id == user_id:
                return user.name

    def add_event(self, event):
        self.events.append(event)

    def __str__(self):
        return "Chat: %d messages" % len(self.events)

    def __iter__(self):
        for event in self.events:
            yield event


class User(object):
    """A hangouts user participating in this chat"""
    def __init__(self, participant):
        self.chat_id = participant['id'].get('chat_id')
        self.gaia_id = participant['id'].get('gaia_id')
        self.name = participant.get('fallback_name', resolve_user(self.gaia_id))

    def __str__(self):
        return "%s (%s)" % (self.name, self.chat_id)


class Event(object):
    """A Hangouts event"""

    def __init__(self, chat, event, logtype="IRC"):
        self.chat = chat
        self.logtype = logtype
        self.sender_id = event['sender_id']['chat_id']
        self.timestamp = event['timestamp']
        self.eventtype = event['event_type']
        # TODO: HANGOUT_EVENT = rings etc
        if "chat_message" in event:
            self.raw_msg = event['chat_message']
        else:
            self.raw_msg = ""

    def _get_msg(self):
        """Combine message segments into one line"""
        if not self.raw_msg: return

        msg = self.raw_msg['message_content']
        output = []
        if "segment" in msg:
            for segment in msg['segment']:
                if segment['type'] == "TEXT" or segment['type'] == "LINK":
                    output.append(segment['text'])
                elif segment['type'] == "LINE_BREAK":
                    output.append("\n")
                else:
                    print(msg)
                    sys.exit(1)
        elif "attachment" in msg:
            for attachment in msg['attachment']:
                attachment_type = attachment['embed_item']['type']
                # It's theoretically possible to have multiple attachment types
                # Haven't seen one though
                if len(attachment_type) > 1:
                    print(attachment)
                    sys.exit(1)
                if attachment_type[0] == "PLUS_PHOTO":
                    output.append("Attachment: %s" % attachment_type)
                else:
                    print(attachment['embed_item'])
                    print(attachment['embed_item'].keys())
                    sys.exit(1)
        else:
            print(self.raw_msg)
            sys.exit(1)

        return "".join(output)

    def __str__(self):
        """Representation of a message"""
        if self.logtype == "IRC":
            return self.log_irc()
        else:
            return "Unknown log type %s" % self.logtype

    def log_irc(self):
        """IRC-style logging"""
        # TODO: Timestamp
        return "<%s> %s" % (self.chat.get_user(self.sender_id), self._get_msg())

# Loop conversations
for conversations in DATA:
    convo_id = conversations['conversation_id']['id']
    convo = conversations['conversation_state']['conversation']
    events = conversations['conversation_state']['event']

    chat = Chat(convo_id, chat_type=convo['type'], participants=convo['participant_data'], name=convo.get('name', None))

    for event in events:
        chat.add_event(Event(chat, event))

    print("Saving log: " + chat.filename)

    chatlog = open(os.path.join(OUTDIR, chat.filename+".log"), 'w')

    for line in chat:
        #chatlog.write(str(line, 'utf-8')+"\n")
        print(line)

    chatlog.close()

