from repository import queue_message


def send_sms(phone_number, message):
    """
    Send an SMS through the PENZI messaging system.

    For the prototype, messages are stored in the database
    outbox instead of being sent through a real SMS provider.
    """
    queue_message(phone_number, message)


def send_sms_list(phone_numbers, message):
    """
    Send the same SMS to multiple phone numbers.
    """
    for phone_number in phone_numbers:
        send_sms(phone_number, message)
