SHORTCODE = "22141"

REGISTRATION_PROMPT = (
    "To register SMS start#name#age#gender#county#town to 22141. "
    "E.g., start#John Doe#26#Male#Nakuru#Naivasha"
)

WELCOME = (
    "Welcome to our dating service with 6000 potential dating partners! "
    + REGISTRATION_PROMPT
)

DETAILS_PROMPT = (
    "SMS details#levelOfEducation#profession#maritalStatus#religion#ethnicity "
    "to 22141. E.g. details#diploma#driver#single#christian#mijikenda"
)

SEARCH_PROMPT = (
    "To search for a MPENZI, SMS match#age#town to 22141 and meet the "
    "person of your dreams. E.g., match#23-25#Nairobi"
)

DESCRIPTION_PROMPT = (
    "This is the last stage of registration. SMS a brief description of "
    "yourself to 22141 starting with the word MYSELF. "
    "E.g., MYSELF chocolate, lovely, sexy etc."
)

INITIAL_DETAILS_ONLY = (
    "You were registered for dating with your initial details. "
    + SEARCH_PROMPT
)

MYSELF_SAVED = (
    "You are now registered for dating. To search for a MPENZI, SMS "
    "match#age#town to 22141 and meet the person of your dreams. "
    "E.g., match#23-25#Kisumu"
)

START_FORMAT = "Invalid format. " + REGISTRATION_PROMPT
DETAILS_FORMAT = "Invalid format. " + DETAILS_PROMPT
MATCH_FORMAT = (
    "Invalid format. SMS match#age#town to 22141. E.g., match#23-25#Nairobi"
)
AGE_RANGE_INVALID = (
    "Invalid age. Use one age or a range, e.g. match#23-25#Nairobi"
)
MYSELF_FORMAT = (
    "Invalid format. SMS MYSELF followed by a short description. "
    "E.g., MYSELF tall, dark and handsome"
)
DESCRIBE_FORMAT = (
    "Invalid format. SMS DESCRIBE followed by the person's number. "
    "E.g., DESCRIBE 0722010203"
)
GENDER_INVALID = "Invalid gender. Please enter Male or Female."
FIELD_TOO_LONG = (
    "One of your entries is too long. Please shorten it and try again."
)
DETAILS_UPDATED = "Your details have been updated."
DESCRIPTION_UPDATED = "Your description has been updated."

NO_MATCHES = (
    "Sorry, we found no one matching that age and place. "
    "Try a wider range, e.g. match#23-35#Nairobi"
)
NO_MORE_MATCHES = (
    "There are no more matches from your last search. "
    "SMS match#age#town to search again."
)
NO_SEARCH = (
    "You have no recent search. SMS match#age#town to 22141. "
    "E.g., match#23-25#Nairobi"
)
NOT_FOUND = "No profile found for that number."
OWN_NUMBER = (
    "That is your own number. SMS another person's number to see their details."
)

OPTED_OUT = (
    "You have been unsubscribed from PENZI and will not receive more "
    "messages. SMS PENZI to 22141 to rejoin."
)
OPTED_OUT_REPLY = "You are unsubscribed from PENZI. SMS PENZI to 22141 to rejoin."
NOT_SUBSCRIBED = "You are not subscribed to PENZI."
SERVER_ERROR = "Sorry, something went wrong. Please try again later."


_WORDS = {
    "Female": {"one": "lady", "many": "ladies", "poss": "her",
               "obj": "her", "subj": "She", "self": "herself"},
    "Male": {"one": "man", "many": "men", "poss": "his",
             "obj": "him", "subj": "He", "self": "himself"},
}

_STEP_HINTS = {
    "new": REGISTRATION_PROMPT,
    "awaiting_details": (
        "SMS details#levelOfEducation#profession#maritalStatus#religion#"
        "ethnicity to 22141 to complete your profile, or SMS match#age#town "
        "to start searching."
    ),
    "awaiting_description": (
        "SMS MYSELF followed by a short description of yourself to 22141 to "
        "finish registering, or SMS match#age#town to start searching."
    ),
    "complete": (
        "SMS match#age#town to 22141 to find a MPENZI. "
        "E.g., match#23-25#Nairobi"
    ),
    "opted_out": "SMS PENZI to 22141 to rejoin.",
}

_VALID_COMMANDS = {
    "new": "PENZI, start#name#age#gender#county#town",
    "awaiting_details": (
        "details#..., match#age#town, NEXT, a phone number, "
        "DESCRIBE <number>, YES, STOP"
    ),
    "awaiting_description": (
        "MYSELF <description>, details#..., match#age#town, NEXT, "
        "a phone number, DESCRIBE <number>, YES, STOP"
    ),
    "complete": (
        "match#age#town, NEXT, a phone number, DESCRIBE <number>, YES, "
        "MYSELF <description>, details#..., STOP"
    ),
    "opted_out": "PENZI",
}


def words(gender):
    return _WORDS.get(gender, _WORDS["Male"])


def first_name(name):
    parts = name.split() if name else []
    return parts[0] if parts else ""


def age_invalid(min_age, max_age):
    return f"Invalid age. Please enter a number between {min_age} and {max_age}."


def description_too_long(limit):
    return f"Your description is too long. Please keep it under {limit} characters."


def no_pending(hours):
    return (
        "You have no pending requests right now. "
        f"Requests expire after {hours} hours."
    )


def profile_created(first):
    return f"Your profile has been created successfully {first}. " + DETAILS_PROMPT


def next_step(stage):
    return _STEP_HINTS.get(stage, REGISTRATION_PROMPT)


def welcome_back(stage):
    return "Welcome back to PENZI! " + next_step(stage)


def unknown_command(stage):
    valid = _VALID_COMMANDS.get(stage, _VALID_COMMANDS["new"])
    return f"Sorry, we didn't understand that. Valid commands: {valid}."


def not_allowed(stage, command):
    if stage == "opted_out":
        return OPTED_OUT_REPLY
    if stage == "new":
        if command == "STOP":
            return NOT_SUBSCRIBED
        return "You need to register first. " + REGISTRATION_PROMPT
    if command == "START":
        return "You are already registered. " + next_step(stage)
    return "You can't do that yet. " + next_step(stage)


def match_header(total, target_gender, example_phone, shown):
    w = words(target_gender)
    if total == 1:
        return (
            f"We have 1 {w['one']} who matches your choice! We will send "
            f"you {w['poss']} details shortly. To get more details about "
            f"a {w['one']}, SMS {w['poss']} number e.g., {example_phone} "
            "to 22141"
        )
    return (
        f"We have {total} {w['many']} who match your choice! We will send "
        f"you details of {shown} of them shortly. To get more details "
        f"about a {w['one']}, SMS {w['poss']} number e.g., {example_phone} "
        "to 22141"
    )


def match_batch(rows, remaining, target_gender):
    w = words(target_gender)
    lines = [f"{r['name']} aged {r['age']}, {r['phone_number']}." for r in rows]
    text = "\n".join(lines)
    if remaining > 0:
        text += (
            f"\nSend NEXT to 22141 to receive details of the remaining "
            f"{remaining} {w['many']}"
        )
    return text


def _cap(text):
    text = text.strip()
    return text[:1].upper() + text[1:]


def _profile_line(u):
    parts = [
        f"{u['name']} aged {u['age']}",
        f"{u['county']} County",
        f"{u['town']} town",
    ]
    if u.get("level_of_education"):
        parts.append(_cap(u["level_of_education"]))
    if u.get("profession"):
        parts.append(_cap(u["profession"]))
    if u.get("marital_status"):
        parts.append(u["marital_status"].strip().lower())
    if u.get("religion"):
        parts.append(_cap(u["religion"]))
    if u.get("ethnicity"):
        parts.append(_cap(u["ethnicity"]))
    return ", ".join(parts)


def profile_reply(u):
    return (
        f"{_profile_line(u)}. Send DESCRIBE {u['phone_number']} to get "
        f"more details about {first_name(u['name'])}."
    )


def interest_notification(requester, target):
    w = words(requester["gender"])
    return (
        f"Hi {first_name(target['name'])}, a {w['one']} called "
        f"{first_name(requester['name'])} is interested in you and "
        f"requested your details. {w['subj']} is aged {requester['age']} "
        f"based in {requester['county']}. Do you want to know more about "
        f"{w['obj']}? Send YES to 22141"
    )


def description_reply(target):
    first = first_name(target["name"])
    if not target.get("self_description"):
        return f"{first} hasn't written a description yet."
    w = words(target["gender"])
    return f"{first} describes {w['self']} as {target['self_description']}"


NOT_ACTIVATED = (
    "Welcome to PENZI, where meaningful connections begin! "
    "To unlock the service, SMS the word PENZI to 22141 "
    "for service activation."
)

START_BAD_FORMAT = (
    "Almost there! To create your profile, SMS "
    "start#name#age#gender#county#town to 22141. "
    "E.g., start#John Doe#26#Male#Nakuru#Naivasha"
)
