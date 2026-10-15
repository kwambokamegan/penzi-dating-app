import re
import traceback

import messages
import repository
import services


def parse_command(text):
    upper = text.upper()
    if upper == "PENZI":
        return "PENZI"
    if upper.startswith("START#"):
        return "START"
    if re.match(r"^START(\s|$)", upper):
        return "START_FORMAT"
    if upper.startswith("DETAILS#"):
        return "DETAILS"
    if re.match(r"^MYSELF(\s|#|$)", upper):
        return "MYSELF"
    if upper.startswith("MATCH#"):
        return "MATCH"
    if upper == "NEXT":
        return "NEXT"
    if re.match(r"^DESCRIBE(\s|#|$)", upper):
        return "DESCRIBE"
    if upper == "YES":
        return "YES"
    if upper == "STOP":
        return "STOP"
    if re.fullmatch(r"\+?\d{9,13}", text.replace(" ", "")):
        return "LOOKUP"
    return None


def _describe_number(text):
    return re.sub(r"^DESCRIBE[\s#]*", "", text, flags=re.IGNORECASE).strip()


def _route(command, user, phone_number, text):
    if command == "PENZI":
        return services.handle_penzi(user)
    if command == "START":
        return services.register(phone_number, text)
    if command == "DETAILS":
        return services.save_details(user, text)
    if command == "MYSELF":
        return services.save_myself(user, text)
    if command == "MATCH":
        return services.search_matches(user, text)
    if command == "NEXT":
        return services.next_matches(user)
    if command == "LOOKUP":
        return services.lookup_profile(user, text.replace(" ", ""))
    if command == "DESCRIBE":
        return services.describe(user, _describe_number(text))
    if command == "YES":
        return services.confirm_interest(user)
    if command == "STOP":
        return services.opt_out(user)
    return messages.unknown_command(services.stage_of(user))


def handle_message(phone_number, message):
    text = (message or "").strip()
    try:
        user = repository.get_user_by_phone(phone_number)
        stage = services.stage_of(user)
        command = parse_command(text)

        # ---- activation gate (only for people not yet registered) ----
        if user is None:
            if command == "PENZI":
                repository.mark_activated(phone_number)
                return _route(command, user, phone_number, text)

            if not repository.is_activated(phone_number):
                return messages.NOT_ACTIVATED

            if command == "START_FORMAT":
                return messages.START_BAD_FORMAT
        elif command == "START_FORMAT":
            return messages.not_allowed(stage, "START")
        # ---------------------------------------------------------------

        if command is None:
            if stage == "opted_out":
                return messages.OPTED_OUT_REPLY
            return messages.unknown_command(stage)

        if command not in services.allowed_commands(stage):
            return messages.not_allowed(stage, command)

        return _route(command, user, phone_number, text)
    except Exception:
        traceback.print_exc()
        return messages.SERVER_ERROR
