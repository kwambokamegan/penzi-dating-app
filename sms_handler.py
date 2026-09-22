def handle_message(phone_number, message):
    message = message.strip()

    if message.upper() == "PENZI":
        return (
            "Welcome to PENZI! Kindly enter your details starting "
            "with START then # followed by your name, age, gender, "
            "county and town separated by #. E.g "
            "START#John Doe#26#Male#Nairobi#Kasarani"
        )

    return "Sorry, we couldn't understand that command."

if __name__ == "__main__":
    reply = handle_message("0712345678", "PENZI")
    print(reply)