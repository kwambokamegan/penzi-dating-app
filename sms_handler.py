from db import get_connection

def handle_message(phone_number, message):
    message = message.strip()

    if message.upper() == "PENZI":
        return (
            "Welcome to PENZI! Kindly enter your details starting "
            "with START then # followed by your name, age, gender, "
            "county and town separated by #. E.g "
            "START#John Doe#26#Male#Nairobi#Kasarani"
        )

    if message.upper().startswith("START#"):
        return handle_start(phone_number, message)

    if message.upper().startswith("DETAILS#"):
        return handle_details(phone_number, message)

    if message.upper() == "MYSELF":
        return handle_myself(phone_number)

    if message.upper().startswith("MATCH#"):
        return handle_match(phone_number, message)

    if message.upper().startswith("DESCRIBE#"):
        return handle_describe(phone_number, message)

    if message.upper().startswith("YES#"):
        return handle_yes(phone_number, message)

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
        return (
            "Invalid format. Please use: "
            "START#Name#Age#Gender#County#Town"
        )

    _, name, age, gender, county, town = parts

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
        f"Thank you {name}, you're registered! Now send your details "
        "with DETAILS#Level of Education#Profession#Marital Status#"
        "Religion#Ethnicity#Phone Number"
    )


def handle_details(phone_number, message):
    parts = message.split("#")

    if len(parts) != 7:
        return (
            "Invalid format. Please use: DETAILS#Level of Education#"
            "Profession#Marital Status#Religion#Ethnicity#Phone Number"
        )

    _, education, profession, marital_status, religion, ethnicity, phone_in_msg = parts

    user, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not user:
        conn.close()
        return (
            "You need to register first. Text START#Name#Age#Gender#"
            "County#Town to begin."
        )

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET level_of_education = %s,
            profession = %s,
            marital_status = %s,
            religion = %s,
            ethnicity = %s,
            registration_stage = %s
        WHERE phone_number = %s
        """,
        (education, profession, marital_status, religion, ethnicity,
         "complete", phone_number)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        "Your details are saved! You can now text MYSELF to see your "
        "profile, or MATCH#Age#County#Town to find a match."
    )


def handle_myself(phone_number):
    user, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not user:
        conn.close()
        return (
            "You are not registered yet. Text START#Name#Age#Gender#"
            "County#Town to begin."
        )

    conn.close()

    return (
        f"Name: {user['name']}\n"
        f"Age: {user['age']}\n"
        f"Gender: {user['gender']}\n"
        f"County: {user['county']}\n"
        f"Town: {user['town']}\n"
        f"Education: {user['level_of_education']}\n"
        f"Profession: {user['profession']}\n"
        f"Marital Status: {user['marital_status']}\n"
        f"Religion: {user['religion']}\n"
        f"Ethnicity: {user['ethnicity']}"
    )


def handle_match(phone_number, message):
    parts = message.split("#")

    if len(parts) != 4:
        return "Invalid format. Please use: MATCH#Age#County#Town"

    _, age, county, town = parts

    requester, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not requester:
        conn.close()
        return (
            "You need to register first. Text START#Name#Age#Gender#"
            "County#Town to begin."
        )

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT name, age, phone_number FROM users
        WHERE age = %s AND county = %s AND town = %s
        AND phone_number != %s
        """,
        (age, county, town, phone_number)
    )
    matches = cursor.fetchall()
    conn.close()

    if not matches:
        return "No matches found for that age, county, and town."

    lines = [f"{m['name']}, {m['age']} - {m['phone_number']}" for m in matches]
    return "Matches found:\n" + "\n".join(lines)


if __name__ == "__main__":
    reply = handle_message("0712345678", "MATCH#24#Nairobi#Kasarani")
    print(reply)


def handle_describe(phone_number, message):
    parts = message.split("#", 1)

    if len(parts) != 2 or not parts[1].strip():
        return "Invalid format. Please use: DESCRIBE#Your description here"

    description = parts[1].strip()

    user, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not user:
        conn.close()
        return (
            "You need to register first. Text START#Name#Age#Gender#"
            "County#Town to begin."
        )

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET self_description = %s WHERE phone_number = %s",
        (description, phone_number)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return "Your description has been saved!"


def handle_yes(phone_number, message):
    parts = message.split("#")

    if len(parts) != 2 or not parts[1].strip():
        return "Invalid format. Please use: YES#PhoneNumber"

    requested_phone = parts[1].strip()

    requester, conn = get_user(phone_number)
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    if not requester:
        conn.close()
        return (
            "You need to register first. Text START#Name#Age#Gender#"
            "County#Town to begin."
        )

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO match_requests (requester_phone, requested_phone, status)
        VALUES (%s, %s, %s)
        """,
        (phone_number, requested_phone, "pending")
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        f"Your request to connect with {requested_phone} has been sent! "
        "We'll notify you once approved."
    )
