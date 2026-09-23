from db import get_connection


def handle_message(phone_number, message):
    message = message.strip()
    upper = message.upper()

    # Stage check: look up the user first so we know where they are in
    # the registration flow before deciding which commands are valid.
    existing_user, stage_conn = get_user(phone_number)
    if stage_conn is not None:
        stage_conn.close()

    is_registered = existing_user is not None

    # A brand-new (unregistered) number can only greet PENZI or START#.
    if not is_registered and not (upper == "PENZI" or upper.startswith("START#")):
        return (
            "You need to register first. SMS start#name#age#gender#county#town "
            "to 22141."
        )

    # An already-registered number shouldn't re-run START#.
    if is_registered and upper.startswith("START#"):
        return "You are already registered with PENZI."

    if upper == "PENZI":
        return (
            "Welcome to our dating service with 6000 potential dating "
            "partners! To register SMS start#name#age#gender#county#town "
            "to 22141. E.g., start#John Doe#26#Male#Nakuru#Naivasha"
        )

    if upper.startswith("START#"):
        return handle_start(phone_number, message)

    if upper.startswith("DETAILS#"):
        return handle_details(phone_number, message)

    if upper.startswith("MYSELF"):
        return handle_myself(phone_number, message)

    if upper.startswith("MATCH#"):
        return handle_match(phone_number, message)

    if upper == "NEXT":
        return handle_next(phone_number)

    if upper.startswith("DESCRIBE"):
        return handle_describe_lookup(phone_number, message)

    if upper == "YES":
        return handle_yes(phone_number)

    if message.isdigit() and len(message) >= 9:
        return handle_phone_lookup(phone_number, message)

    return "Sorry, we couldn't understand that command."


def get_user(phone_number):
    conn = get_connection()
    if conn is None:
        return None, None
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE phone_number = %s", (phone_number,)
    )
    user = cursor.fetchone()
    return user, conn


def handle_start(phone_number, message):
    parts = message.split("#")

    if len(parts) != 6:
        return "Invalid format. Please use: start#name#age#gender#county#town"

    _, name, age, gender, county, town = parts

    if not age.isdigit() or not (18 <= int(age) <= 100):
        return "Invalid age. Please enter a valid age between 18 and 100."

    gender = gender.strip().capitalize()
    if gender not in ("Male", "Female"):
        return "Invalid gender. Please enter Male or Female."

    user, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if user:
        conn.close()
        return "You are already registered with PENZI."

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users
        (phone_number, registration_stage, name, age, gender, county, town)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (phone_number, "awaiting_details", name, age, gender, county, town)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        f"Your profile has been created successfully {name.split()[0]}. "
        "SMS details#levelOfEducation#profession#maritalStatus#religion#"
        "ethnicity to 22141."
    )


def handle_details(phone_number, message):
    parts = message.split("#")

    if len(parts) != 6:
        return (
            "Invalid format. Please use: details#levelOfEducation#"
            "profession#maritalStatus#religion#ethnicity"
        )

    _, education, profession, marital_status, religion, ethnicity = parts

    user, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not user:
        conn.close()
        return "You need to register first. SMS start#name#age#gender#county#town."

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET level_of_education = %s, profession = %s, marital_status = %s,
            religion = %s, ethnicity = %s, registration_stage = %s
        WHERE phone_number = %s
        """,
        (education, profession, marital_status, religion, ethnicity,
         "awaiting_description", phone_number)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        "You were registered for dating with your initial details. "
        "To search for a MPENZI, SMS match#age-age#town to 22141. "
        "E.g., match#23-25#Nairobi"
    )


def handle_myself(phone_number, message):
    parts = message.split(" ", 1)

    if len(parts) != 2 or not parts[1].strip():
        return "Invalid format. Please use: MYSELF <your description>"

    description = parts[1].strip()

    user, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not user:
        conn.close()
        return "You need to register first. SMS start#name#age#gender#county#town."

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users SET self_description = %s, registration_stage = %s
        WHERE phone_number = %s
        """,
        (description, "complete", phone_number)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        "You are now registered for dating. To search for a MPENZI, "
        "SMS match#age-age#town to 22141. E.g., match#23-25#Kisumu"
    )


def handle_match(phone_number, message):
    parts = message.split("#")

    if len(parts) != 3 or "-" not in parts[1]:
        return "Invalid format. Please use: match#age-age#town"

    _, age_range, town = parts
    try:
        age_min, age_max = [int(x) for x in age_range.split("-")]
    except ValueError:
        return "Invalid age range. Please use: match#23-25#town"

    requester, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not requester:
        conn.close()
        return "You need to register first. SMS start#name#age#gender#county#town."

    opposite_gender = "Female" if requester["gender"] == "Male" else "Male"

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT phone_number FROM users
        WHERE age BETWEEN %s AND %s AND county = %s AND gender = %s
        AND phone_number != %s
        """,
        (age_min, age_max, town, opposite_gender, phone_number)
    )
    results = cursor.fetchall()

    if not results:
        cursor.close()
        conn.close()
        return "No matches found for that age range and town."

    search_cursor = conn.cursor()
    search_cursor.execute(
        """
        INSERT INTO match_searches (requester_phone, age_min, age_max, town, shown_count)
        VALUES (%s, %s, %s, %s, 0)
        """,
        (phone_number, age_min, age_max, town)
    )
    search_id = search_cursor.lastrowid

    for i, row in enumerate(results):
        search_cursor.execute(
            "INSERT INTO match_results (search_id, phone_number, position) VALUES (%s, %s, %s)",
            (search_id, row["phone_number"], i)
        )
    conn.commit()

    reply = format_match_batch(cursor, search_id, 0, len(results))

    search_cursor.execute(
        "UPDATE match_searches SET shown_count = 3 WHERE id = %s", (search_id,)
    )
    conn.commit()
    cursor.close()
    search_cursor.close()
    conn.close()

    total = len(results)
    header = f"We have {total} {opposite_gender.lower()}s who match your choice! We will send you details of {min(3, total)} of them shortly.\n"
    return header + reply


def format_match_batch(cursor, search_id, start, total):
    cursor.execute(
        """
        SELECT u.name, u.age, u.phone_number FROM match_results mr
        JOIN users u ON u.phone_number = mr.phone_number
        WHERE mr.search_id = %s AND mr.position >= %s AND mr.position < %s
        ORDER BY mr.position
        """,
        (search_id, start, start + 3)
    )
    batch = cursor.fetchall()
    lines = [f"{m['name']} aged {m['age']}, {m['phone_number']}." for m in batch]
    remaining = total - (start + len(batch))
    text = "\n".join(lines)
    if remaining > 0:
        text += f"\nSend NEXT to 22141 to receive details of the remaining {remaining}."
    return text


def handle_next(phone_number):
    conn = get_connection()
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, shown_count FROM match_searches
        WHERE requester_phone = %s ORDER BY id DESC LIMIT 1
        """,
        (phone_number,)
    )
    search = cursor.fetchone()

    if not search:
        conn.close()
        return "You have no recent search. SMS match#age-age#town to start one."

    cursor.execute(
        "SELECT COUNT(*) AS total FROM match_results WHERE search_id = %s",
        (search["id"],)
    )
    total = cursor.fetchone()["total"]

    if search["shown_count"] >= total:
        conn.close()
        return "You've seen all the matches for your last search."

    reply = format_match_batch(cursor, search["id"], search["shown_count"], total)

    update_cursor = conn.cursor()
    new_count = min(search["shown_count"] + 3, total)
    update_cursor.execute(
        "UPDATE match_searches SET shown_count = %s WHERE id = %s",
        (new_count, search["id"])
    )
    conn.commit()
    cursor.close()
    update_cursor.close()
    conn.close()

    return reply


def handle_phone_lookup(phone_number, target_phone):
    target, conn = get_user(target_phone)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not target:
        conn.close()
        return "No profile found for that number."

    requester, _ = get_user(phone_number)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO interest_requests (requester_phone, target_phone, status)
        VALUES (%s, %s, %s)
        """,
        (phone_number, target_phone, "notified")
    )
    conn.commit()
    cursor.close()
    conn.close()

    if requester:
        notify = (
            f"Hi {target['name'].split()[0]}, a man called {requester['name']} "
            f"is interested in you and requested your details. He is aged "
            f"{requester['age']} based in {requester['town']}. Do you want to "
            "know more about him? Send YES to 22141"
        )

    return (
        f"{target['name']} aged {target['age']}, {target['county']} County, "
        f"{target['town']} town, {target['level_of_education']}, "
        f"{target['profession']}, {target['marital_status']}, "
        f"{target['religion']}, {target['ethnicity']}. Send DESCRIBE "
        f"{target_phone} to get more details about {target['name'].split()[0]}."
    )


def handle_describe_lookup(phone_number, message):
    parts = message.split(" ", 1)

    if len(parts) != 2 or not parts[1].strip():
        return "Invalid format. Please use: DESCRIBE <phone number>"

    target_phone = parts[1].strip()

    target, conn = get_user(target_phone)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not target:
        conn.close()
        return "No profile found for that number."

    conn.close()

    if not target["self_description"]:
        return f"{target['name']} hasn't written a description yet."

    return (
        f"{target['name'].split()[0]} describes herself as "
        f"{target['self_description']}"
        if target["gender"] == "Female" else
        f"{target['name'].split()[0]} describes himself as "
        f"{target['self_description']}"
    )


def handle_yes(phone_number):
    conn = get_connection()
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT * FROM interest_requests
        WHERE target_phone = %s AND status = 'notified'
        ORDER BY id DESC LIMIT 1
        """,
        (phone_number,)
    )
    req = cursor.fetchone()

    if not req:
        conn.close()
        return "You have no pending interest requests right now."

    requester_cursor = conn.cursor(dictionary=True)
    requester_cursor.execute(
        "SELECT * FROM users WHERE phone_number = %s", (req["requester_phone"],)
    )
    requester = requester_cursor.fetchone()

    update_cursor = conn.cursor()
    update_cursor.execute(
        "UPDATE interest_requests SET status = 'revealed' WHERE id = %s",
        (req["id"],)
    )
    conn.commit()
    cursor.close()
    requester_cursor.close()
    update_cursor.close()
    conn.close()

    if not requester:
        return "Sorry, that person's profile is no longer available."

    return (
        f"{requester['name']} aged {requester['age']}, {requester['county']} "
        f"County, {requester['town']} town, {requester['level_of_education']}, "
        f"{requester['profession']}, {requester['marital_status']}, "
        f"{requester['religion']}, {requester['ethnicity']}. Send DESCRIBE "
        f"{requester['phone_number']} to get more details about "
        f"{requester['name'].split()[0]}."
    )
