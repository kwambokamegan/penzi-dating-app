p = "test_spec.py"
t = open(p, encoding="utf-8").read()

if "0a START before PENZI" in t:
    print("already patched")
else:
    reset = '''# reset activation state for the test numbers
for _p in (JAMAL, MARIA, STRANGER, LATE):
    repository._run_write(
        "DELETE FROM activations WHERE phone = %s", (_p,))

check("0a START before PENZI is blocked", JAMAL,
      "start#Jamal Jalang'o#33#Male#Testland#Bamburi",
      ["unlock the service", "SMS the word PENZI to 22141"])
check("0b bare START before PENZI is blocked", JAMAL, "START",
      ["SMS the word PENZI to 22141"])

'''
    old13 = '''check("13 unregistered cannot match", STRANGER, "match#20-30#Nairobi",
      ["You need to register first."])'''
    new13 = '''check("13a unactivated cannot match", STRANGER, "match#20-30#Nairobi",
      ["SMS the word PENZI to 22141"])
check("13b PENZI activates", STRANGER, "PENZI", ["Welcome to our dating service"])
check("13c bare START after PENZI", STRANGER, "START",
      ["Almost there!", "start#name#age#gender#county#town to 22141"])
check("13d activated but unregistered cannot match", STRANGER,
      "match#20-30#Nairobi", ["You need to register first."])'''

    for label, anchor in [("test 1", 'check("1 PENZI welcome"'),
                          ("test 5", 'check("5 Maria start"'),
                          ("test 16", 'check("16 start only, no details"'),
                          ("test 13", old13)]:
        if anchor not in t:
            print("!! could not find", label)

    t = t.replace('check("1 PENZI welcome"', reset + 'check("1 PENZI welcome"', 1)
    t = t.replace('check("5 Maria start"',
        'check("4b Maria PENZI", MARIA, "PENZI", ["Welcome to our dating service"])\ncheck("5 Maria start"', 1)
    t = t.replace('check("16 start only, no details"',
        'check("15b Late PENZI", LATE, "PENZI", ["Welcome to our dating service"])\ncheck("16 start only, no details"', 1)
    t = t.replace(old13, new13, 1)
    open(p, "w", encoding="utf-8").write(t)
    print("patched")
