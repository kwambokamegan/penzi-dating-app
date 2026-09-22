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


if __name__ == "__main__":
    reply = handle_message("0712345678", "MYSELF")
    print(reply)