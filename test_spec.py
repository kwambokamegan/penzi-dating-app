import repository
import services
from sms_handler import handle_message

JAMAL = "0790000001"
MARIA = "0790000002"
STRANGER = "0790000003"
LATE = "0790000004"

passed = 0
failed = 0


def report(label, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"PASS  {label}")
    else:
        failed += 1
        print(f"FAIL  {label}")
        print(detail)


def check(label, who, text, must_contain):
    reply = handle_message(who, text)
    missing = [m for m in must_contain if m not in reply]
    report(label, not missing,
           f"      sent: {text}\n      got : {reply}\n      missing: {missing}")


def outbox_has(label, phone, snippet):
    notes = repository.get_undelivered(phone)
    ok = any(snippet in n["message"] for n in notes)
    report(label, ok, f"      outbox for {phone}: {[n['message'] for n in notes]}")


check("1 PENZI welcome", JAMAL, "PENZI", [
    "Welcome to our dating service with 6000 potential dating partners!",
    "start#name#age#gender#county#town to 22141",
    "E.g., start#John Doe#26#Male#Nakuru#Naivasha"])

check("2 start", JAMAL, "start#Jamal Jalang'o#33#Male#Testland#Bamburi", [
    "Your profile has been created successfully Jamal.",
    "details#levelOfEducation#profession#maritalStatus#religion#ethnicity to 22141",
    "E.g. details#diploma#driver#single#christian#mijikenda"])

check("3 details", JAMAL, "details#graduate#accountant#divorced#muslim#somali", [
    "This is the last stage of registration.",
    "starting with the word MYSELF"])

check("4 MYSELF", JAMAL, "MYSELF tall, dark and handsome", [
    "You are now registered for dating.",
    "match#age#town to 22141",
    "E.g., match#23-25#Kisumu"])

check("5 Maria start", MARIA, "start#Maria Mwende#31#Female#Testland#Testville",
      ["Your profile has been created successfully Maria."])
check("6 Maria details", MARIA, "details#graduate#nurse#single#christian#kamba",
      ["This is the last stage of registration."])
check("7 Maria MYSELF", MARIA,
      "MYSELF Diligent, loving, dedicated and will make you tick",
      ["You are now registered for dating."])

check("8 match", JAMAL, "match#30-32#Testville", [
    "We have 1 lady who matches your choice!",
    "Maria Mwende aged 31, 0790000002."])

check("9 phone number lookup", JAMAL, MARIA, [
    "Maria Mwende aged 31, Testland County, Testville town, Graduate, Nurse, single, Christian, Kamba.",
    "Send DESCRIBE 0790000002 to get more details about Maria."])

outbox_has("9b Maria is informed", MARIA,
    "Hi Maria, a man called Jamal is interested in you and requested your details. "
    "He is aged 33 based in Testland. Do you want to know more about him? "
    "Send YES to 22141")

check("10 DESCRIBE", JAMAL, f"DESCRIBE {MARIA}", [
    "Maria describes herself as Diligent, loving, dedicated and will make you tick"])

check("11 YES", MARIA, "YES", [
    "Jamal Jalang'o aged 33, Testland County, Bamburi town, Graduate, Accountant, divorced, Muslim, Somali.",
    "Send DESCRIBE 0790000001 to get more details about Jamal."])

check("12 second YES has nothing pending", MARIA, "YES", ["no pending requests"])
check("13 unregistered cannot match", STRANGER, "match#20-30#Nairobi",
      ["You need to register first."])
check("14 unknown command lists valid ones", JAMAL, "hello", ["Valid commands:"])
check("15 already registered", JAMAL, "start#Again#30#Male#X#Y",
      ["You are already registered."])

check("16 start only, no details", LATE, "start#Late Larry#40#Male#Testland#Testville",
      ["Your profile has been created successfully Late."])
services.send_details_followups(minutes=0)
outbox_has("16b follow-up message sent", LATE,
           "You were registered for dating with your initial details.")
check("17 can search without details", LATE, "match#30-32#Testville",
      ["We have 1 lady"])

print(f"\n{passed} passed, {failed} failed")
