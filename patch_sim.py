p = "simulator.html"
t = open(p, encoding="utf-8").read()

if "greetIfNew" in t:
    print("already patched")
elif "</script>" not in t:
    print("!! could not find </script>")
else:
    block = r'''
        /* WELCOME MESSAGE WHEN A NEW NUMBER IS ENTERED */
        let lastGreeted = "";
        let greetTimer = null;

        async function greetIfNew() {

            const phone =
                document.getElementById("phone").value.trim();

            const looksLikeNumber =
                /^\+?\d{9,13}$/.test(phone.replace(/\s/g, ""));

            if (!looksLikeNumber || phone === lastGreeted) {
                return;
            }

            lastGreeted = phone;

            /* a new number starts a fresh conversation */
            document.getElementById("messages").innerHTML = "";

            try {
                const response = await fetch(
                    "http://localhost:5000/api/greeting/" +
                    encodeURIComponent(phone)
                );

                if (!response.ok) {
                    return;
                }

                const data = await response.json();

                if (data.reply) {
                    addBubble(data.reply, "received");
                }

            } catch (error) {
                console.error(error);
            }
        }

        document.getElementById("phone").addEventListener("input", () => {
            clearTimeout(greetTimer);
            greetTimer = setTimeout(greetIfNew, 600);
        });

        document.getElementById("phone").addEventListener("change", greetIfNew);

'''
    t = t.replace("</script>", block + "    </script>", 1)
    open(p, "w", encoding="utf-8").write(t)
    print("patched")
