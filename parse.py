import json
import sys

print "Parsing data..."
data = json.loads(file("Hangouts.json").read())
print "Done"

# [u'continuation_end_timestamp', u'conversation_state']

data = data['conversation_state']

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

def get_names(data):
    members = []
    for person in data:
        name = users.get(person['id']['chat_id'], None)
        if name:
            members.append(name)
            continue
        else:
            print "CACHE MISS"
        if person.has_key('fallback_name'):
            users[person['id']['chat_id']] = person['fallback_name']
            members.append(person['fallback_name'])

    return members

class Event(object):
    def __init__(self, event, logtype="IRC"):
        self.logtype = logtype
        self.sender_id = event['sender_id']['chat_id']
        self.timestamp = event['timestamp']
        self.eventtype = event['event_type']
        # TODO: HANGOUT_EVENT = rings etc
        if event.has_key("chat_message"):
            self.raw_msg = event['chat_message']
        else:
            self.raw_msg = ""

    def _get_msg(self):
        """Combine message segments into one line"""
        if not self.raw_msg: return

        msg = self.raw_msg['message_content']
        output = []
        if msg.has_key('segment'):
            for segment in msg['segment']:
                if segment['type'] == "TEXT" or segment['type'] == "LINK":
                    output.append(segment['text'])
                elif segment['type'] == "LINE_BREAK":
                    output.append("\n")
                else:
                    print msg
                    sys.exit(1)
        elif msg.has_key('attachment'):
            for attachment in msg['attachment']:
                attachment_type = attachment['embed_item']['type']
                # It's theoretically possible to have multiple attachment types
                # Haven't seen one though
                if len(attachment_type) > 1:
                    print attachment
                    sys.exit(1)
                if attachment_type[0] == "PLUS_PHOTO":
                    output.append("Attachment: %s" % attachment_type)
                else:
                    print attachment['embed_item']
                    print attachment['embed_item'].keys()
                    sys.exit(1)
        else:
            print self.raw_msg
            sys.exit(1)

        return u"".join(output)

    def __str__(self):
        """Representation of a message"""
        if self.logtype == "IRC":
            return self.log_irc()
        else:
            return "Unknown log type %s" % self.logtype
    def log_irc(self):
        out = "<%s> %s" % (users.get(self.sender_id, "UNDEF"), self._get_msg())
        return out.encode("UTF-8")

# Loop conversations
for conversations in data:
    convo = conversations['conversation_state']['conversation']
    events = conversations['conversation_state']['event']

    convo_type = convo['type']

    if convo_type == "STICKY_ONE_TO_ONE":
        print "One on one chat: %s" % get_names(convo['participant_data'])
    elif convo_type == "GROUP":
        if convo.has_key('name'):
            print "Named Group Chat %s, %d participants: %s" % (convo['name'], len(convo['participant_data']), get_names(convo['participant_data']))
        else:
            print "Group Chat, %d participants: %s" % (len(convo['participant_data']), get_names(convo['participant_data']))
    else:
        print "UNKNOWN TYPE: %s" % convo_type


    log = []
    for event in events:
        log.append(Event(event))
        # print users.get(event['sender_id']['chat_id'], "Unknown user")
        # print event['timestamp']
        # print event['event_type']
        # print event['chat_message']

    for line in log:
        print line

#    sys.exit(1)




