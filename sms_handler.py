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

    return "Sorry, we couldn't understand that command."


def handle_start(phone_number, message):
    parts = message.split("#")

    if len(parts) != 6:
        return (
            "Invalid format. Please use: "
            "START#Name#Age#Gender#County#Town"
        )

    _, name, age, gender, county, town = parts

    conn = get_connection()
    if conn is None:
        return "Sorry, something went wrong. Please try again later."

    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE phone_number = %s", (phone_number,)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.close()
        conn.close()
        return "You are already registered with PENZI."

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


if __name__ == "__main__":
    reply = handle_message(
        "0712345678", "START#John Doe#26#Male#Nairobi#Kasarani"
    )
    print(reply)