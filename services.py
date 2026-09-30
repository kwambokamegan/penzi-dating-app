import re

import gateway
import messages
import repository

# ---- Business rules: change a rule here and nowhere else ----
MIN_AGE = 18
MAX_AGE = 100
MATCH_BATCH_SIZE = 3
REQUEST_EXPIRY_HOURS = 24
DETAILS_FOLLOWUP_MINUTES = 5
MAX_DESCRIPTION_LENGTH = 300
DETAIL_LIMITS = (50, 50, 20, 30, 30)

# Stages allowed to search and contact people.
# Set to {"complete"} if searching should need a fully finished profile.
SEARCHABLE_STAGES = {"awaiting_details", "awaiting_description", "complete"}
REGISTERED_STAGES = {"awaiting_details", "awaiting_description", "complete"}

REGISTRATION_COMMANDS = {
    "new": {"PENZI", "START"},
    "awaiting_details": {"PENZI", "DETAILS"},
    "awaiting_description": {"PENZI", "DETAILS", "MYSELF"},
    "complete": {"PENZI", "DETAILS", "MYSELF"},
    "opted_out": {"PENZI"},
}
SEARCH_COMMANDS = {"MATCH", "NEXT", "LOOKUP", "DESCRIBE", "YES"}


def stage_of(user):
    if user is None:
        return "new"
    if user["opted_out"]:
        return "opted_out"
    return user["registration_stage"]


def allowed_commands(stage):
    allowed = set(REGISTRATION_COMMANDS.get(stage, {"PENZI"}))
    if stage in SEARCHABLE_STAGES:
        allowed |= SEARCH_COMMANDS
    if stage in REGISTERED_STAGES:
        allowed.add("STOP")
    return allowed


# ---------- REGISTRATION ----------

def handle_penzi(user):
    stage = stage_of(user)
    if stage == "new":
        return messages.WELCOME
    if stage == "opted_out":
        repository.set_opted_out(user["phone_number"], False)
        stage = user["registration_stage"]
    return messages.welcome_back(stage)


def register(phone_number, text):
    parts = [p.strip() for p in text.split("#")]
    if len(parts) != 6 or not all(parts[1:]):
        return messages.START_FORMAT
    _, name, age, gender, county, town = parts
    if not age.isdigit() or not (MIN_AGE <= int(age) <= MAX_AGE):
        return messages.age_invalid(MIN_AGE, MAX_AGE)
    gender = gender.capitalize()
    if gender not in ("Male", "Female"):
        return messages.GENDER_INVALID
    if len(name) > 50 or len(county) > 50 or len(town) > 50:
        return messages.FIELD_TOO_LONG
    repository.create_user(
        phone_number, name, int(age), gender, county, town, "awaiting_details"
    )
    return messages.profile_created(messages.first_name(name))


def save_details(user, text):
    parts = [p.strip() for p in text.split("#")]
    if len(parts) != 6 or not all(parts[1:]):
        return messages.DETAILS_FORMAT
    values = parts[1:]
    if any(len(v) > limit for v, limit in zip(values, DETAIL_LIMITS)):
        return messages.FIELD_TOO_LONG
    already_complete = user["registration_stage"] == "complete"
    new_stage = "complete" if already_complete else "awaiting_description"
    repository.save_details(user["phone_number"], *values, new_stage)
    if already_complete:
        return messages.DETAILS_UPDATED
    return messages.DESCRIPTION_PROMPT


def save_myself(user, text):
    description = re.sub(r"^MYSELF[\s#]*", "", text, flags=re.IGNORECASE).strip()
    if not description:
        return messages.MYSELF_FORMAT
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return messages.description_too_long(MAX_DESCRIPTION_LENGTH)
    was_complete = user["registration_stage"] == "complete"
    repository.save_description(user["phone_number"], description, "complete")
    if was_complete:
        return messages.DESCRIPTION_UPDATED
    return messages.MYSELF_SAVED


def send_details_followups(minutes=DETAILS_FOLLOWUP_MINUTES):
    users = repository.get_users_needing_followup(minutes)
    for u in users:
        gateway.send_sms(u["phone_number"], messages.INITIAL_DETAILS_ONLY)
        repository.mark_followup_sent(u["phone_number"])
    return len(users)


# ---------- MATCHING ----------

def parse_age_range(text):
    text = text.strip()
    if text.isdigit():
        low = high = int(text)
    elif re.fullmatch(r"\d+\s*-\s*\d+", text):
        low, high = [int(x) for x in re.split(r"\s*-\s*", text)]
    else:
        return None
    if low > high or low < MIN_AGE or high > MAX_AGE:
        return None
    return low, high


def _opposite_gender(user):
    return "Female" if user["gender"] == "Male" else "Male"


def search_matches(user, text):
    parts = [p.strip() for p in text.split("#")]
    if len(parts) != 3 or not parts[2]:
        return messages.MATCH_FORMAT
    age_range = parse_age_range(parts[1])
    if age_range is None:
        return messages.AGE_RANGE_INVALID
    place = parts[2]
    target_gender = _opposite_gender(user)
    found = repository.find_matches(
        age_range[0], age_range[1], place, target_gender, user["phone_number"]
    )
    if not found:
        return messages.NO_MATCHES
    search_id = repository.create_search(
        user["phone_number"], age_range[0], age_range[1], place
    )
    repository.add_search_results(search_id, [r["phone_number"] for r in found])
    batch = repository.get_search_batch(search_id, 0, MATCH_BATCH_SIZE)
    repository.set_shown_count(search_id, len(batch))
    total = len(found)
    header = messages.match_header(
        total, target_gender, batch[0]["phone_number"], len(batch)
    )
    body = messages.match_batch(batch, total - len(batch), target_gender)
    return header + "\n\n" + body


def next_matches(user):
    search = repository.get_latest_search(user["phone_number"])
    if not search:
        return messages.NO_SEARCH
    total = repository.count_search_results(search["id"])
    shown = search["shown_count"]
    if shown >= total:
        return messages.NO_MORE_MATCHES
    batch = repository.get_search_batch(search["id"], shown, MATCH_BATCH_SIZE)
    repository.set_shown_count(search["id"], shown + len(batch))
    remaining = total - shown - len(batch)
    return messages.match_batch(batch, remaining, _opposite_gender(user))


# ---------- CONTACT ----------

def lookup_profile(user, target_phone):
    if target_phone == user["phone_number"]:
        return messages.OWN_NUMBER
    target = repository.get_user_by_phone(target_phone)
    if target is None or target["opted_out"]:
        return messages.NOT_FOUND
    already = repository.find_recent_interest(
        user["phone_number"], target_phone, REQUEST_EXPIRY_HOURS
    )
    if not already:
        repository.create_interest(user["phone_number"], target_phone)
        gateway.send_sms(
            target_phone, messages.interest_notification(user, target)
        )
    return messages.profile_reply(target)


def describe(user, number):
    if not re.fullmatch(r"\+?\d{9,13}", number):
        return messages.DESCRIBE_FORMAT
    target = repository.get_user_by_phone(number)
    if target is None or target["opted_out"]:
        return messages.NOT_FOUND
    return messages.description_reply(target)


def confirm_interest(user):
    pending = repository.get_pending_interest_for(
        user["phone_number"], REQUEST_EXPIRY_HOURS
    )
    if pending is None:
        return messages.no_pending(REQUEST_EXPIRY_HOURS)
    repository.mark_interest_revealed(pending["id"])
    requester = repository.get_user_by_phone(pending["requester_phone"])
    if requester is None or requester["opted_out"]:
        return messages.NOT_FOUND
    return messages.profile_reply(requester)


def opt_out(user):
    repository.set_opted_out(user["phone_number"], True)
    return messages.OPTED_OUT


# ---------- DASHBOARD AND OUTBOX (used by server.py) ----------

def dashboard_stats():
    return repository.get_dashboard_stats()


def recent_users():
    return repository.list_recent_users()


def recent_interests():
    return repository.list_recent_interests()


def pending_messages_for(phone_number):
    rows = repository.get_undelivered(phone_number)
    repository.mark_delivered([r["id"] for r in rows])
    return rows
