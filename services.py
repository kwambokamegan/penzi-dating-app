import hashlib
import hmac
import re
import secrets

import gateway
import messages
import repository

# ---- Business rules: change a rule here and nowhere else ----
MIN_AGE = 18
MAX_AGE = 100
MATCH_BATCH_SIZE = 3
REQUEST_EXPIRY_HOURS = 24
LOGIN_CODE_MINUTES = 5
LOGIN_CODE_WINDOW_MINUTES = 10
LOGIN_MAX_CODES = 3
LOGIN_MAX_ATTEMPTS = 5
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
    return (messages.profile_reply(target) + " "
            + messages.request_sent(target, personal_link(user["phone_number"])))


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
    ok, reply = respond_to_interest(user, pending["id"], True)
    return reply


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


# ---------- WEB LOGIN ----------

def _clean_phone(phone_number):
    return re.sub(r"\s+", "", phone_number or "")


def _hash_code(phone_number, code):
    return hashlib.sha256(f"{phone_number}:{code}".encode()).hexdigest()


def request_login_code(phone_number):
    phone_number = _clean_phone(phone_number)
    if not re.fullmatch(r"\+?\d{9,13}", phone_number):
        return messages.LOGIN_CODE_SENT
    user = repository.get_user_by_phone(phone_number)
    if user is None or user["opted_out"]:
        return messages.LOGIN_CODE_SENT
    recent = repository.count_recent_login_codes(
        phone_number, LOGIN_CODE_WINDOW_MINUTES
    )
    if recent >= LOGIN_MAX_CODES:
        return messages.LOGIN_CODE_SENT
    code = f"{secrets.randbelow(1000000):06d}"
    repository.save_login_code(
        phone_number, _hash_code(phone_number, code), LOGIN_CODE_MINUTES
    )
    gateway.send_sms(
        phone_number, messages.login_code_text(code, LOGIN_CODE_MINUTES)
    )
    return messages.LOGIN_CODE_SENT


def verify_login_code(phone_number, code):
    phone_number = _clean_phone(phone_number)
    code = (code or "").strip()
    active = repository.get_active_login_code(phone_number)
    if active is None:
        return None, messages.LOGIN_CODE_INVALID
    if active["attempts"] >= LOGIN_MAX_ATTEMPTS:
        return None, messages.LOGIN_TOO_MANY_ATTEMPTS
    expected = active["code_hash"]
    if not hmac.compare_digest(expected, _hash_code(phone_number, code)):
        repository.add_login_attempt(active["id"])
        return None, messages.LOGIN_CODE_INVALID
    repository.mark_login_code_used(active["id"])
    user = repository.get_user_by_phone(phone_number)
    if user is None or user["opted_out"]:
        return None, messages.LOGIN_CODE_INVALID
    return user, None


# ---------- INBOX ----------

def my_interests(user):
    incoming = []
    rows = repository.list_incoming_interests(
        user["phone_number"], REQUEST_EXPIRY_HOURS
    )
    for r in rows:
        if r["status"] == "revealed":
            status = "accepted"
        elif r["status"] == "declined":
            status = "declined"
        else:
            status = "pending" if r["active"] else "expired"
        item = {
            "id": r["id"],
            "name": messages.first_name(r["name"]),
            "age": r["age"],
            "county": r["county"],
            "status": status,
            "created_at": r["created_at"],
            "profile": None,
            "phone": r["requester_phone"] if r["status"] == "revealed" else None,
        }
        if status == "accepted":
            requester = repository.get_user_by_phone(r["requester_phone"])
            if requester:
                item["profile"] = messages.profile_reply(requester)
        incoming.append(item)

    outgoing = []
    rows = repository.list_outgoing_interests(
        user["phone_number"], REQUEST_EXPIRY_HOURS
    )
    for r in rows:
        if r["status"] == "revealed":
            status = "accepted"
        elif r["status"] == "declined":
            status = "declined"
        else:
            status = "pending" if r["active"] else "expired"
        item = {
            "id": r["id"],
            "name": messages.first_name(r["name"]),
            "age": r["age"],
            "county": r["county"],
            "status": status,
            "created_at": r["created_at"],
            "message": None,
            "phone": r["target_phone"] if r["status"] == "revealed" else None,
        }
        if status == "accepted":
            target = repository.get_user_by_phone(r["target_phone"])
            if target:
                item["message"] = messages.accepted_notice(target, user)
        outgoing.append(item)

    return {"incoming": incoming, "outgoing": outgoing}


def respond_to_interest(user, interest_id, accept):
    interest = repository.get_interest(interest_id)
    if interest is None or interest["target_phone"] != user["phone_number"]:
        return False, messages.INTEREST_NOT_FOUND
    if interest["status"] != "notified":
        return False, messages.INTEREST_ALREADY_ANSWERED
    active = repository.get_active_interest(
        interest_id, user["phone_number"], REQUEST_EXPIRY_HOURS
    )
    if active is None:
        return False, messages.INTEREST_EXPIRED
    requester = repository.get_user_by_phone(interest["requester_phone"])
    if requester is None or requester["opted_out"]:
        return False, messages.INTEREST_NOT_FOUND
    if not accept:
        repository.set_interest_status(interest_id, "declined")
        return True, messages.INTEREST_DECLINED
    repository.set_interest_status(interest_id, "revealed")
    gateway.send_sms(
        requester["phone_number"],
        messages.accepted_notice(
            user, requester, personal_link(requester["phone_number"])
        )
    )
    return True, (
        messages.profile_reply(requester)
        + "\n\n"
        + messages.match_wish(requester)
    )


def user_by_phone(phone_number):
    user = repository.get_user_by_phone(phone_number)
    if user is None or user["opted_out"]:
        return None
    return user


def decline_interest(user):
    pending = repository.get_pending_interest_for(
        user["phone_number"], REQUEST_EXPIRY_HOURS
    )
    if pending is None:
        return messages.no_pending(REQUEST_EXPIRY_HOURS)
    ok, reply = respond_to_interest(user, pending["id"], False)
    return reply


# ---------- PASSWORD LOGIN ----------

from werkzeug.security import check_password_hash, generate_password_hash

PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_FAILS = 5
PASSWORD_LOCK_MINUTES = 10


def login_with_password(phone_number, password):
    phone_number = _clean_phone(phone_number)
    password = password or ""
    user = user_by_phone(phone_number)
    if user is None:
        return None, messages.LOGIN_PASSWORD_INVALID
    state = repository.get_password_state(phone_number)
    if state is None or not state["password_hash"] or state["locked"]:
        return None, messages.LOGIN_PASSWORD_INVALID
    if not check_password_hash(state["password_hash"], password):
        repository.record_failed_login(
            phone_number, PASSWORD_MAX_FAILS, PASSWORD_LOCK_MINUTES
        )
        return None, messages.LOGIN_PASSWORD_INVALID
    repository.clear_failed_logins(phone_number)
    return user, None


def set_password_with_code(phone_number, code, new_password):
    new_password = new_password or ""
    if len(new_password) < PASSWORD_MIN_LENGTH:
        return None, messages.PASSWORD_TOO_SHORT
    user, error = verify_login_code(phone_number, code)
    if error:
        return None, error
    repository.set_password_hash(
        user["phone_number"], generate_password_hash(new_password)
    )
    return user, None


# ---------- PERSONAL SETUP LINK ----------

def setup_token(phone_number):
    import os
    key = os.getenv("SECRET_KEY", "").encode()
    msg = f"setup:{phone_number}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:24]


def personal_link(phone_number):
    """Setup link for people with no password yet, plain login link otherwise."""
    base = messages.login_link()
    state = repository.get_password_state(phone_number)
    if state is not None and not state["password_hash"]:
        return f"{base}?p={phone_number}&t={setup_token(phone_number)}"
    if state is not None:
        return f"{base}?p={phone_number}"
    return base


def setup_user(phone_number, token):
    phone_number = _clean_phone(phone_number)
    user = repository.get_user_by_phone(phone_number)
    if user is None or user["opted_out"]:
        return None
    state = repository.get_password_state(phone_number)
    if state is None or state["password_hash"]:
        return None
    if not hmac.compare_digest(str(token or ""), setup_token(phone_number)):
        return None
    return user


def set_first_password(phone_number, token, new_password):
    new_password = new_password or ""
    if len(new_password) < PASSWORD_MIN_LENGTH:
        return None, f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    user = setup_user(phone_number, token)
    if user is None:
        return None, "This setup link is not valid. If you already set a password, please log in."
    repository.set_password_hash(
        user["phone_number"], generate_password_hash(new_password)
    )
    return user, None
