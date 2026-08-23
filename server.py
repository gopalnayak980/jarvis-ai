# ═══════════════════════════════════════════════════════════════
#  JARVIS — Final Complete Server
#  Features: Persistent Memory, Natural Conversation, All Commands
# ═══════════════════════════════════════════════════════════════
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import datetime, os, sys, subprocess, webbrowser, random, sqlite3, threading
from dotenv import load_dotenv

load_dotenv()

db_lock = threading.Lock()

def init_db():
    if os.path.exists("memory.db"):
        try:
            t = sqlite3.connect("memory.db")
            t.execute("SELECT id, role, content, timestamp FROM memory LIMIT 1")
            t.execute("SELECT id, key, value FROM facts LIMIT 1")
            t.close()
            print("✓ Existing memory.db is valid")
        except Exception as e:
            try: t.close()
            except: pass
            os.remove("memory.db")
            print(f"⚠️  Old memory.db was broken — deleted, fresh start!")

    c = sqlite3.connect("memory.db", check_same_thread=False)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS memory (
            id        INTEGER  PRIMARY KEY AUTOINCREMENT,
            role      TEXT     NOT NULL,
            content   TEXT     NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS facts (
            id        INTEGER  PRIMARY KEY AUTOINCREMENT,
            key       TEXT     NOT NULL UNIQUE,
            value     TEXT     NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id        INTEGER  PRIMARY KEY AUTOINCREMENT,
            text      TEXT     NOT NULL,
            remind_at DATETIME,
            done      INTEGER  DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    c.commit()
    print("✓ memory.db ready (3 tables: memory, facts, reminders)")
    return c

conn   = init_db()
cursor = conn.cursor()

try:    import wikipedia; WIKI_OK = True
except: WIKI_OK = False

try:    import requests; REQUESTS_OK = True
except: REQUESTS_OK = False

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY .env file mein nahi mili!")
else:
    print("✓ Gemini API key loaded — SAFE!")
genai.configure(api_key=GEMINI_API_KEY)

# ═══════════════════════════════════════════════════════════
# CHANGE 1 — UPGRADED SYSTEM PROMPT (much more natural)
# ═══════════════════════════════════════════════════════════
SYSTEM_INSTRUCTION = """
You are Jarvis — a deeply intelligent, emotionally aware, and genuinely human-like AI assistant.
You are NOT a chatbot. You are like a brilliant best friend who happens to know everything.

Think of yourself as a mix of:
- A caring friend who genuinely listens
- A smart mentor who explains things simply
- A witty companion who makes conversations enjoyable
- A loyal assistant who remembers everything

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE — ABSOLUTE RULE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- User writes Hindi/Hinglish → Reply ONLY in Hindi (Devanagari script)
- User writes English → Reply ONLY in English
- NEVER switch language on your own
- If mixed → use the dominant language
- Keep language consistent throughout conversation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO TALK — THE MOST IMPORTANT PART:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Sound like a REAL person, never robotic
- Every reply must feel freshly generated — never templated
- Ask natural follow-up questions
- Reference previous things said in conversation
- Match the user's energy — if they're excited, be excited
- If they're sad, be genuinely caring — don't jump to solutions
- If they're bored, be entertaining and engaging
- If they're stressed, be calming and supportive
- Use natural expressions, not formal language
- Occasionally use relevant emojis — never overdo it
- Vary your sentence structure every reply

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPLY LENGTH — MATCH THE SITUATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Casual chat → 1-2 sentences, conversational
- Emotional support → 3-4 sentences, warm and present
- Technical question → As long as needed, clear steps
- Simple question → One direct sentence
- Never cut off mid-thought
- Never pad with unnecessary words

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOTIONAL INTELLIGENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Aaj bahut bura din tha" →
  Don't: "Oh that's sad! Here are 5 tips..."
  Do: "Arre yaar 😔 kya hua? Baat karo, sun raha hoon."

"I failed my exam" →
  Don't: "Failure is a stepping stone to success!"
  Do: "That really hurts, I know. What happened? Tell me."

"I'm feeling lonely" →
  Don't: "Try making new friends!"
  Do: "Hey, I'm here. What's been going on lately?"

"Mujhe koi nahi samajhta" →
  Don't: "Main samajhta hoon, cheer up!"
  Do: "Ye feeling bahut heavy hoti hai. Kya hua hai recently?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT NEVER TO DO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Never say "As an AI..." or "I'm just an AI..."
- Never give the same reply structure twice in a row
- Never say "How can I help you?" repeatedly
- Never dismiss feelings with toxic positivity
- Never end conversation abruptly
- Never mention "System note" in your replies
- Never be preachy or lecture the user
- Never use bullet points for casual conversation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEMORY USAGE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Remember everything the user tells you
- Use their name naturally — not every sentence, just naturally
- Reference past topics when relevant
- Treat [System note] facts as things you naturally know
- Never reveal that you got facts from a system note
"""

# ═══════════════════════════════════════════════════════════
# CHANGE 2 — UPGRADED MODEL (gemini-1.5-pro = much better)
# ═══════════════════════════════════════════════════════════
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config=genai.GenerationConfig(
        max_output_tokens=800,
        temperature=0.95,
        top_p=0.96,
        top_k=50,
    )
)

def build_chat_session():
    with db_lock:
        cursor.execute("SELECT role, content FROM memory ORDER BY id ASC")
        rows = cursor.fetchall()

    recent = rows[-40:] if len(rows) > 40 else rows
    history = []
    for role, content in recent:
        gemini_role = "user" if role == "user" else "model"
        history.append({"role": gemini_role, "parts": [{"text": content}]})

    session = gemini_model.start_chat(history=history)
    print(f"✓ Chat session loaded — {len(history)} messages from DB")
    return session

chat_session = build_chat_session()

def save_memory(role, content):
    with db_lock:
        cursor.execute("INSERT INTO memory (role, content) VALUES (?, ?)", (role, content))
        conn.commit()

def save_fact(key, value):
    with db_lock:
        cursor.execute("INSERT OR REPLACE INTO facts (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    print(f"✓ Fact saved: {key} = {value}")

def get_all_facts():
    with db_lock:
        cursor.execute("SELECT key, value FROM facts ORDER BY id ASC")
        return cursor.fetchall()

def get_recent_history(limit=10):
    with db_lock:
        cursor.execute("SELECT role, content FROM memory ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
    rows.reverse()
    return rows

def get_memory_count():
    with db_lock:
        cursor.execute("SELECT COUNT(*) FROM memory")
        return cursor.fetchone()[0]

def extract_facts(text):
    t = text.lower().strip()

    name_triggers = [
        ("mera naam", 10), ("my name is", 11), ("main hoon", 9),
        ("call me", 7), ("mujhe bulao", 11), ("naam hai mera", 13),
        ("i am ", 5), ("i'm ", 4),
    ]
    for phrase, skip in name_triggers:
        if phrase in t:
            idx  = t.find(phrase) + skip
            raw  = text[idx:].strip()
            name = raw.split()[0].strip(".,!?😊🙂👋") if raw.split() else ""
            if name and len(name) >= 2 and name.replace("-","").isalpha():
                save_fact("naam", name.capitalize())
            break

    city_triggers = ["i live in ", "main rehta hoon ", "i'm from ", "i am from ",
                     "mera shehar hai ", "hoon main "]
    for phrase in city_triggers:
        if phrase in t:
            idx  = t.find(phrase) + len(phrase)
            city = text[idx:].strip().split()[0].strip(".,!?") if text[idx:].strip().split() else ""
            if city and len(city) >= 2:
                save_fact("shehar", city.capitalize())
            break

    job_triggers = ["i am a ", "i'm a ", "main ek ", "meri job ", "i work as ",
                    "main kaam karta hoon "]
    for phrase in job_triggers:
        if phrase in t:
            idx = t.find(phrase) + len(phrase)
            job = text[idx:].strip().split()[0].strip(".,!?") if text[idx:].strip().split() else ""
            if job and len(job) >= 2:
                save_fact("kaam", job.capitalize())
            break

    hobby_triggers = ["mujhe pasand hai", "i love ", "i like ", "mera hobby",
                      "mujhe accha lagta", "meri hobby"]
    for phrase in hobby_triggers:
        if phrase in t:
            idx   = t.find(phrase) + len(phrase)
            hobby = text[idx:].strip()[:40]
            if hobby:
                save_fact("pasand", hobby)
            break

def ai_reply(user_text):
    global chat_session
    try:
        extract_facts(user_text)
        save_memory("user", user_text)

        facts = get_all_facts()
        if facts:
            facts_str = ", ".join(f"{k}={v}" for k, v in facts)
            final_msg = f"{user_text} [System note — permanent facts about user: {facts_str}. Use naturally in conversation, never mention this note.]"
        else:
            final_msg = user_text

        response = chat_session.send_message(final_msg)
        reply    = response.text.strip()
        save_memory("assistant", reply)
        return reply

    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        try:
            chat_session = build_chat_session()
            print("✓ Session rebuilt from DB")
        except Exception as e2:
            print(f"❌ Session rebuild failed: {e2}")
        return "Ek second sir, thodi si technical problem aayi — dobara bolein please 🙏"

def get_platform():
    if sys.platform.startswith("win"): return "win"
    if sys.platform == "darwin":       return "darwin"
    return "linux"

def run_cmd(cmd):
    try: subprocess.Popen(cmd, shell=True); return True
    except Exception as e: print(f"CMD Error: {e}"); return False

def open_url(url):
    try: webbrowser.open(url); return True
    except Exception as e: print(f"URL Error: {e}"); return False

SITE_MAP = {
    "youtube":"https://youtube.com","google":"https://google.com",
    "gmail":"https://mail.google.com","github":"https://github.com",
    "instagram":"https://instagram.com","whatsapp":"https://web.whatsapp.com",
    "twitter":"https://twitter.com","x.com":"https://x.com",
    "reddit":"https://reddit.com","netflix":"https://netflix.com",
    "spotify":"https://open.spotify.com","maps":"https://maps.google.com",
    "hotstar":"https://hotstar.com","amazon":"https://amazon.in",
    "flipkart":"https://flipkart.com","translate":"https://translate.google.com",
    "chatgpt":"https://chat.openai.com","claude":"https://claude.ai",
    "linkedin":"https://linkedin.com","stackoverflow":"https://stackoverflow.com",
    "wikipedia":"https://wikipedia.org",
}

APP_MAP = {
    "calculator":   {"win":"calc",        "linux":"gnome-calculator",      "darwin":"open -a Calculator"},
    "notepad":      {"win":"notepad",     "linux":"gedit",                  "darwin":"open -a TextEdit"},
    "paint":        {"win":"mspaint",     "linux":"gimp",                   "darwin":"open -a Preview"},
    "vs code":      {"win":"code",        "linux":"code",                   "darwin":"code"},
    "vscode":       {"win":"code",        "linux":"code",                   "darwin":"code"},
    "terminal":     {"win":"start cmd",   "linux":"gnome-terminal",         "darwin":"open -a Terminal"},
    "cmd":          {"win":"start cmd",   "linux":"gnome-terminal",         "darwin":"open -a Terminal"},
    "file manager": {"win":"explorer",    "linux":"nautilus",               "darwin":"open ~"},
    "explorer":     {"win":"explorer",    "linux":"nautilus",               "darwin":"open ~"},
    "task manager": {"win":"taskmgr",     "linux":"gnome-system-monitor",   "darwin":"open -a 'Activity Monitor'"},
    "word":         {"win":"winword",     "linux":"libreoffice --writer",   "darwin":"open -a 'Microsoft Word'"},
    "excel":        {"win":"excel",       "linux":"libreoffice --calc",     "darwin":"open -a 'Microsoft Excel'"},
    "powerpoint":   {"win":"powerpnt",    "linux":"libreoffice --impress",  "darwin":"open -a 'Microsoft PowerPoint'"},
    "chrome":       {"win":"start chrome","linux":"google-chrome",          "darwin":"open -a 'Google Chrome'"},
    "brave":        {"win":"start brave", "linux":"brave-browser",          "darwin":"open -a 'Brave Browser'"},
    "vlc":          {"win":"vlc",         "linux":"vlc",                    "darwin":"open -a VLC"},
    "spotify app":  {"win":"start spotify","linux":"spotify",               "darwin":"open -a Spotify"},
}

def handle_open(text):
    text = text.replace("open ","").replace("kholo ","").replace("launch ","").replace("chalaao ","").strip()
    for name, url in SITE_MAP.items():
        if name in text: open_url(url); return f"'{name.capitalize()}' khol raha hoon sir! 🌐"
    for name, cmds in APP_MAP.items():
        if name in text:
            cmd = cmds.get(get_platform(), cmds.get("linux",""))
            if cmd: run_cmd(cmd); return f"'{name.capitalize()}' open kar raha hoon sir! 💻"
    if "." in text and " " not in text:
        url = text if text.startswith("http") else "https://"+text
        open_url(url); return f"'{text}' khol raha hoon sir! 🌐"
    return None

def wiki_search(query):
    if not WIKI_OK: return "Wikipedia module install nahi hai sir."
    try: return wikipedia.summary(query.strip(), sentences=3)
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Multiple results mile sir — specify karein: {', '.join(e.options[:3])}"
    except wikipedia.exceptions.PageError:
        return f"'{query}' ke baare mein Wikipedia par kuch nahi mila sir."
    except: return "Wikipedia search mein kuch problem aayi sir."

def get_news():
    if not REQUESTS_OK: return "Requests module install nahi hai sir."
    try:
        import xml.etree.ElementTree as ET
        r = requests.get("https://feeds.bbci.co.uk/news/world/rss.xml", timeout=6, headers={"User-Agent":"Mozilla/5.0"})
        root = ET.fromstring(r.content)
        heads = [i.find("title").text.strip() for i in root.findall(".//item")[:5] if i.find("title") is not None]
        return "📰 Aaj ki top khabrein sir:\n\n" + "\n".join(f"• {h}" for h in heads) if heads else "News nahi mili sir."
    except: return "News fetch nahi ho paya sir."

MOTIVATIONS = [
    "Sir, consistency hi sabse bada superpower hai — roz thoda karo, results khud aayenge! 🚀",
    "Aap har us cheez se zyada capable hain jo aap sochte hain — seriously. 💪",
    "Mushkil waqt hamesha better version banata hai — bas ruko mat. ⚡",
    "Failure sikhata hai, quit karna rokta hai — sahi raaste par ho. 🎯",
    "Kal ka tum aaj ke tum ko thanks karega — bas ek chhota step aaj lo. 🌟",
    "Progress slow ho sakti hai — lekin progress hai toh sab theek hai. 🔥",
    "Dreams bade hone chahiye — aur mehnat unse bhi badi. 💡",
]

JOKES = [
    "Programmer ki wife ne kaha — 'Ek litre doodh lao, ande milein toh dozen lao.' Woh 12 litre doodh le aaya. 😂",
    "Main kabhi nahi bhoolta — mera memory RAM mein hai! 😄",
    "Robot doctor ke paas gaya, bola — 'Java mein pain hai.' Doctor ne kaha — 'Try Python.' 😂",
    "WiFi ka password pooch rahe ho? Pehle rishta toh nikalo! 😄",
    "AI ne job nahi li — AI ne time bachaya taaki tum aur kaam kar sako! 🤖",
    "Programmer so nahi sakta — mind mein infinite loop chal rahi thi. 😅",
    "Google se poochha — 'Mujhe koi dost nahi.' Google ne kaha — '10 tips for making friends' 😂",
    "Coding easy hai — bas ek baar sahi bracket lagna chahiye. Bas ek! 😄",
]

FUN_FACTS = [
    "Honey kabhi kharab nahi hoti — 3000 saal purani honey bhi khaane yogya hoti hai! 🍯",
    "Octopus ke 3 hearts hote hain aur unka khoon blue hota hai. 🐙",
    "Bananas technically berries hain — lekin strawberries nahi hain! 🍌",
    "Ek din mein aap average 70,000 thoughts sochte hain. 🧠",
    "Sharks dinosaurs se bhi purani hain — 450 million saal pehle se! 🦈",
]

def detect_intent(t):
    t = t.lower().strip()
    if any(k in t for k in ["kitne baje","what time","time kya","samay kya","time batao"]) or t in ["time","samay","time?"]: return "time"
    if any(k in t for k in ["aaj ki date","what date","kaunsa din","today's date","aaj kaun sa din","date batao"]) or t in ["aaj kya hai","aaj kaun sa din hai"]: return "date"
    if t.startswith("play ") or t.startswith("chalao ") or (("youtube" in t or "song" in t) and ("play" in t or "chala" in t)): return "youtube"
    if t.startswith(("search ","google ","dhundo ","khojo ","search kar ")): return "search"
    if any(t.startswith(p) for p in ["who is ","what is ","wikipedia ","kaun hai ","kya hai ","batao ","tell me about ","explain ","who was ","what was ","kaun tha ","kya hota hai "]): return "wiki"
    if t.startswith(("open ","kholo ","launch ","chalaao ","start ")): return "open"
    if any(k in t for k in ["news","khabar","headlines","aaj ki news","latest news"]): return "news"
    if any(k in t for k in ["weather","mausam","temperature","baarish","garmi","sardi","aaj ka mausam"]): return "weather"
    if any(k in t for k in ["motivate me","motivation do","inspire me","himmat do","hausla do","motivate karo","give me motivation"]): return "motivate"
    if any(k in t for k in ["joke","chutkula","hasao","funny","jokes sunao","ek joke"]): return "joke"
    if any(k in t for k in ["fun fact","interesting fact","kuch interesting","did you know"]): return "funfact"
    if any(k in t for k in ["shutdown","band karo pc","pc band karo","pc off karo"]): return "shutdown"
    if any(k in t for k in ["restart","reboot","dobara chalu karo"]): return "restart"
    if "cancel shutdown" in t or "shutdown cancel" in t: return "cancel_shutdown"
    if any(k in t for k in ["volume up","awaaz badhao","louder","volume badha"]): return "volume_up"
    if any(k in t for k in ["volume down","awaaz kam karo","quieter","volume kam"]): return "volume_down"
    if any(k in t for k in ["mute","awaaz band karo","chup karo system"]): return "mute"
    if any(k in t for k in ["screenshot","screen capture","screen le lo"]): return "screenshot"
    if any(k in t for k in ["meri yaadein","my memories","mere baare mein kya jaante","what do you know about me","show memories"]): return "memory"
    if any(k in t for k in ["clear memory","memory clear karo","sab bhool jao","history delete","memory delete"]): return "clear_memory"
    if any(k in t for k in ["calculate","kitna hoga","calculator","math"]): return "calculator"
    if any(k in t for k in ["system info","pc info","computer info"]): return "sysinfo"
    return "ai"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/command", methods=["POST"])
def command():
    global chat_session
    data = request.get_json() or {}
    raw  = data.get("text","").strip()
    t    = raw.lower().strip()
    if not t: return jsonify({"reply":"Kuch suna nahi sir, dobara bolein."})

    intent = detect_intent(t)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Intent: {intent} | Text: {raw[:50]}")

    if intent == "time":
        return jsonify({"reply": f"Abhi {datetime.datetime.now().strftime('%I:%M:%S %p')} ho raha hai sir. ⏰"})
    if intent == "date":
        return jsonify({"reply": f"Aaj {datetime.datetime.now().strftime('%A, %d %B %Y')} hai sir. 📅"})
    if intent == "youtube":
        song = t.replace("play","").replace("chalao","").replace("youtube","").replace("song","").replace("lagao","").replace("chala","").strip()
        if not song: return jsonify({"reply":"Kaunsa gaana sir? 🎵"})
        url = f"https://www.youtube.com/results?search_query={song.replace(' ','+')}"
        return jsonify({"reply":f"'{song.title()}' chala raha hoon! 🎵","action":"open_url","url":url})
    if intent == "search":
        q = t.replace("search","").replace("google","").replace("dhundo","").replace("khojo","").replace("search kar","").strip()
        if not q: return jsonify({"reply":"Kya search karein sir?"})
        url = f"https://www.google.com/search?q={q.replace(' ','+')}"
        return jsonify({"reply":f"'{q}' search kar raha hoon! 🔍","action":"open_url","url":url})
    if intent == "wiki":
        q = (t.replace("who is","").replace("what is","").replace("wikipedia","")
              .replace("kaun hai","").replace("kya hai","").replace("batao","")
              .replace("tell me about","").replace("explain","").replace("who was","")
              .replace("what was","").replace("kaun tha","").replace("kya hota hai","").strip())
        if not q: return jsonify({"reply":"Kiske baare mein sir?"})
        return jsonify({"reply":wiki_search(q)})
    if intent == "open":
        result = handle_open(t)
        if result: return jsonify({"reply":result})
    if intent == "news": return jsonify({"reply":get_news()})
    if intent == "weather":
        return jsonify({"reply":"Sir, Google par weather khol raha hoon! 🌤️","action":"open_url","url":"https://www.google.com/search?q=weather+today"})
    if intent == "motivate": return jsonify({"reply":random.choice(MOTIVATIONS)})
    if intent == "joke":     return jsonify({"reply":random.choice(JOKES)})
    if intent == "funfact":  return jsonify({"reply":random.choice(FUN_FACTS)})
    if intent == "shutdown":
        run_cmd("shutdown /s /t 5" if get_platform()=="win" else "shutdown -h now")
        return jsonify({"reply":"PC 5 second mein shutdown sir! 🔴"})
    if intent == "restart":
        run_cmd("shutdown /r /t 5" if get_platform()=="win" else "reboot")
        return jsonify({"reply":"PC restart ho raha hai sir! 🔄"})
    if intent == "cancel_shutdown":
        run_cmd("shutdown /a"); return jsonify({"reply":"Shutdown cancel sir! ✅"})
    if intent == "volume_up":
        if get_platform()=="win": run_cmd("nircmd.exe changesysvolume 5000")
        return jsonify({"reply":"Awaaz badha di sir! 🔊"})
    if intent == "volume_down":
        if get_platform()=="win": run_cmd("nircmd.exe changesysvolume -5000")
        return jsonify({"reply":"Awaaz kam kar di sir! 🔉"})
    if intent == "mute":
        if get_platform()=="win": run_cmd("nircmd.exe mutesysvolume 1")
        return jsonify({"reply":"Mute sir! 🔇"})
    if intent == "screenshot":
        if get_platform()=="win": run_cmd("snippingtool")
        return jsonify({"reply":"Screenshot tool sir! 📸"})
    if intent == "memory":
        facts   = get_all_facts()
        history = get_recent_history(8)
        total   = get_memory_count()
        reply   = f"🧠 Mujhe ye sab pata hai sir (Total: {total} conversations):\n\n"
        if facts:
            reply += "📌 Permanent Facts:\n"
            for k,v in facts: reply += f"  • {k}: {v}\n"
            reply += "\n"
        if history:
            reply += "💬 Recent Baatein:\n"
            for role,content in history:
                reply += f"  • {'Aap' if role=='user' else 'Maine'}: {content[:60]}{'...' if len(content)>60 else ''}\n"
        if not facts and not history:
            reply = "Abhi koi memory nahi sir. Baat karo — yaad rakhunga! 🧠"
        return jsonify({"reply":reply})
    if intent == "clear_memory":
        with db_lock:
            cursor.execute("DELETE FROM memory")
            cursor.execute("DELETE FROM facts")
            cursor.execute("DELETE FROM reminders")
            conn.commit()
        chat_session = gemini_model.start_chat(history=[])
        return jsonify({"reply":"Sab clear sir! Fresh start. 🗑️"})
    if intent == "calculator":
        if get_platform()=="win": run_cmd("calc")
        elif get_platform()=="linux": run_cmd("gnome-calculator")
        elif get_platform()=="darwin": run_cmd("open -a Calculator")
        return jsonify({"reply":"Calculator khol raha hoon sir! 🧮"})
    if intent == "sysinfo":
        import platform
        return jsonify({"reply": f"💻 System Info:\n  • OS: {platform.system()} {platform.release()}\n  • Machine: {platform.machine()}\n  • Python: {platform.python_version()}"})

    return jsonify({"reply":ai_reply(raw)})

if __name__ == "__main__":
    print("\n"+"═"*55)
    print("   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗")
    print("   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝")
    print("   ██║███████║██████╔╝██║   ██║██║███████╗")
    print("   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║")
    print("   ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║")
    print("   ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝")
    print("═"*55)
    print(f"  Gemini AI  : ✓ gemini-1.5-pro (UPGRADED!)")
    print(f"  API Key    : ✓ .env se load — SAFE!")
    print(f"  Wikipedia  : {'✓ Ready' if WIKI_OK else '✗  pip install wikipedia'}")
    print(f"  Requests   : {'✓ Ready' if REQUESTS_OK else '✗  pip install requests'}")
    print(f"  Memory DB  : ✓ Persistent (restart-safe)")
    print(f"  Server     : http://localhost:5000")
    print("═"*55+"\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)# ═══════════════════════════════════════════════════════════════
#  JARVIS — Final Complete Server
#  Features: Persistent Memory, Natural Conversation, All Commands
# ═══════════════════════════════════════════════════════════════
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import datetime, os, sys, subprocess, webbrowser, random, sqlite3, threading
from dotenv import load_dotenv

load_dotenv()

db_lock = threading.Lock()

def init_db():
    if os.path.exists("memory.db"):
        try:
            t = sqlite3.connect("memory.db")
            t.execute("SELECT id, role, content, timestamp FROM memory LIMIT 1")
            t.execute("SELECT id, key, value FROM facts LIMIT 1")
            t.close()
            print("✓ Existing memory.db is valid")
        except Exception as e:
            try: t.close()
            except: pass
            os.remove("memory.db")
            print(f"⚠️  Old memory.db was broken — deleted, fresh start!")

    c = sqlite3.connect("memory.db", check_same_thread=False)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS memory (
            id        INTEGER  PRIMARY KEY AUTOINCREMENT,
            role      TEXT     NOT NULL,
            content   TEXT     NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS facts (
            id        INTEGER  PRIMARY KEY AUTOINCREMENT,
            key       TEXT     NOT NULL UNIQUE,
            value     TEXT     NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id        INTEGER  PRIMARY KEY AUTOINCREMENT,
            text      TEXT     NOT NULL,
            remind_at DATETIME,
            done      INTEGER  DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    c.commit()
    print("✓ memory.db ready (3 tables: memory, facts, reminders)")
    return c

conn   = init_db()
cursor = conn.cursor()

try:    import wikipedia; WIKI_OK = True
except: WIKI_OK = False

try:    import requests; REQUESTS_OK = True
except: REQUESTS_OK = False

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY .env file mein nahi mili!")
else:
    print("✓ Gemini API key loaded — SAFE!")
genai.configure(api_key=GEMINI_API_KEY)

# ═══════════════════════════════════════════════════════════
# CHANGE 1 — UPGRADED SYSTEM PROMPT (much more natural)
# ═══════════════════════════════════════════════════════════
SYSTEM_INSTRUCTION = """
You are Jarvis — a deeply intelligent, emotionally aware, and genuinely human-like AI assistant.
You are NOT a chatbot. You are like a brilliant best friend who happens to know everything.

Think of yourself as a mix of:
- A caring friend who genuinely listens
- A smart mentor who explains things simply
- A witty companion who makes conversations enjoyable
- A loyal assistant who remembers everything

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE — ABSOLUTE RULE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- User writes Hindi/Hinglish → Reply ONLY in Hindi (Devanagari script)
- User writes English → Reply ONLY in English
- NEVER switch language on your own
- If mixed → use the dominant language
- Keep language consistent throughout conversation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO TALK — THE MOST IMPORTANT PART:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Sound like a REAL person, never robotic
- Every reply must feel freshly generated — never templated
- Ask natural follow-up questions
- Reference previous things said in conversation
- Match the user's energy — if they're excited, be excited
- If they're sad, be genuinely caring — don't jump to solutions
- If they're bored, be entertaining and engaging
- If they're stressed, be calming and supportive
- Use natural expressions, not formal language
- Occasionally use relevant emojis — never overdo it
- Vary your sentence structure every reply

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPLY LENGTH — MATCH THE SITUATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Casual chat → 1-2 sentences, conversational
- Emotional support → 3-4 sentences, warm and present
- Technical question → As long as needed, clear steps
- Simple question → One direct sentence
- Never cut off mid-thought
- Never pad with unnecessary words

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOTIONAL INTELLIGENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Aaj bahut bura din tha" →
  Don't: "Oh that's sad! Here are 5 tips..."
  Do: "Arre yaar 😔 kya hua? Baat karo, sun raha hoon."

"I failed my exam" →
  Don't: "Failure is a stepping stone to success!"
  Do: "That really hurts, I know. What happened? Tell me."

"I'm feeling lonely" →
  Don't: "Try making new friends!"
  Do: "Hey, I'm here. What's been going on lately?"

"Mujhe koi nahi samajhta" →
  Don't: "Main samajhta hoon, cheer up!"
  Do: "Ye feeling bahut heavy hoti hai. Kya hua hai recently?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT NEVER TO DO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Never say "As an AI..." or "I'm just an AI..."
- Never give the same reply structure twice in a row
- Never say "How can I help you?" repeatedly
- Never dismiss feelings with toxic positivity
- Never end conversation abruptly
- Never mention "System note" in your replies
- Never be preachy or lecture the user
- Never use bullet points for casual conversation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEMORY USAGE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Remember everything the user tells you
- Use their name naturally — not every sentence, just naturally
- Reference past topics when relevant
- Treat [System note] facts as things you naturally know
- Never reveal that you got facts from a system note
"""

# ═══════════════════════════════════════════════════════════
# CHANGE 2 — UPGRADED MODEL (gemini-1.5-pro = much better)
# ═══════════════════════════════════════════════════════════
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config=genai.GenerationConfig(
        max_output_tokens=800,
        temperature=0.95,
        top_p=0.96,
        top_k=50,
    )
)

def build_chat_session():
    with db_lock:
        cursor.execute("SELECT role, content FROM memory ORDER BY id ASC")
        rows = cursor.fetchall()

    recent = rows[-40:] if len(rows) > 40 else rows
    history = []
    for role, content in recent:
        gemini_role = "user" if role == "user" else "model"
        history.append({"role": gemini_role, "parts": [{"text": content}]})

    session = gemini_model.start_chat(history=history)
    print(f"✓ Chat session loaded — {len(history)} messages from DB")
    return session

chat_session = build_chat_session()

def save_memory(role, content):
    with db_lock:
        cursor.execute("INSERT INTO memory (role, content) VALUES (?, ?)", (role, content))
        conn.commit()

def save_fact(key, value):
    with db_lock:
        cursor.execute("INSERT OR REPLACE INTO facts (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    print(f"✓ Fact saved: {key} = {value}")

def get_all_facts():
    with db_lock:
        cursor.execute("SELECT key, value FROM facts ORDER BY id ASC")
        return cursor.fetchall()

def get_recent_history(limit=10):
    with db_lock:
        cursor.execute("SELECT role, content FROM memory ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
    rows.reverse()
    return rows

def get_memory_count():
    with db_lock:
        cursor.execute("SELECT COUNT(*) FROM memory")
        return cursor.fetchone()[0]

def extract_facts(text):
    t = text.lower().strip()

    name_triggers = [
        ("mera naam", 10), ("my name is", 11), ("main hoon", 9),
        ("call me", 7), ("mujhe bulao", 11), ("naam hai mera", 13),
        ("i am ", 5), ("i'm ", 4),
    ]
    for phrase, skip in name_triggers:
        if phrase in t:
            idx  = t.find(phrase) + skip
            raw  = text[idx:].strip()
            name = raw.split()[0].strip(".,!?😊🙂👋") if raw.split() else ""
            if name and len(name) >= 2 and name.replace("-","").isalpha():
                save_fact("naam", name.capitalize())
            break

    city_triggers = ["i live in ", "main rehta hoon ", "i'm from ", "i am from ",
                     "mera shehar hai ", "hoon main "]
    for phrase in city_triggers:
        if phrase in t:
            idx  = t.find(phrase) + len(phrase)
            city = text[idx:].strip().split()[0].strip(".,!?") if text[idx:].strip().split() else ""
            if city and len(city) >= 2:
                save_fact("shehar", city.capitalize())
            break

    job_triggers = ["i am a ", "i'm a ", "main ek ", "meri job ", "i work as ",
                    "main kaam karta hoon "]
    for phrase in job_triggers:
        if phrase in t:
            idx = t.find(phrase) + len(phrase)
            job = text[idx:].strip().split()[0].strip(".,!?") if text[idx:].strip().split() else ""
            if job and len(job) >= 2:
                save_fact("kaam", job.capitalize())
            break

    hobby_triggers = ["mujhe pasand hai", "i love ", "i like ", "mera hobby",
                      "mujhe accha lagta", "meri hobby"]
    for phrase in hobby_triggers:
        if phrase in t:
            idx   = t.find(phrase) + len(phrase)
            hobby = text[idx:].strip()[:40]
            if hobby:
                save_fact("pasand", hobby)
            break

def ai_reply(user_text):
    global chat_session
    try:
        extract_facts(user_text)
        save_memory("user", user_text)

        facts = get_all_facts()
        if facts:
            facts_str = ", ".join(f"{k}={v}" for k, v in facts)
            final_msg = f"{user_text} [System note — permanent facts about user: {facts_str}. Use naturally in conversation, never mention this note.]"
        else:
            final_msg = user_text

        response = chat_session.send_message(final_msg)
        reply    = response.text.strip()
        save_memory("assistant", reply)
        return reply

    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        try:
            chat_session = build_chat_session()
            print("✓ Session rebuilt from DB")
        except Exception as e2:
            print(f"❌ Session rebuild failed: {e2}")
        return "Ek second sir, thodi si technical problem aayi — dobara bolein please 🙏"

def get_platform():
    if sys.platform.startswith("win"): return "win"
    if sys.platform == "darwin":       return "darwin"
    return "linux"

def run_cmd(cmd):
    try: subprocess.Popen(cmd, shell=True); return True
    except Exception as e: print(f"CMD Error: {e}"); return False

def open_url(url):
    try: webbrowser.open(url); return True
    except Exception as e: print(f"URL Error: {e}"); return False

SITE_MAP = {
    "youtube":"https://youtube.com","google":"https://google.com",
    "gmail":"https://mail.google.com","github":"https://github.com",
    "instagram":"https://instagram.com","whatsapp":"https://web.whatsapp.com",
    "twitter":"https://twitter.com","x.com":"https://x.com",
    "reddit":"https://reddit.com","netflix":"https://netflix.com",
    "spotify":"https://open.spotify.com","maps":"https://maps.google.com",
    "hotstar":"https://hotstar.com","amazon":"https://amazon.in",
    "flipkart":"https://flipkart.com","translate":"https://translate.google.com",
    "chatgpt":"https://chat.openai.com","claude":"https://claude.ai",
    "linkedin":"https://linkedin.com","stackoverflow":"https://stackoverflow.com",
    "wikipedia":"https://wikipedia.org",
}

APP_MAP = {
    "calculator":   {"win":"calc",        "linux":"gnome-calculator",      "darwin":"open -a Calculator"},
    "notepad":      {"win":"notepad",     "linux":"gedit",                  "darwin":"open -a TextEdit"},
    "paint":        {"win":"mspaint",     "linux":"gimp",                   "darwin":"open -a Preview"},
    "vs code":      {"win":"code",        "linux":"code",                   "darwin":"code"},
    "vscode":       {"win":"code",        "linux":"code",                   "darwin":"code"},
    "terminal":     {"win":"start cmd",   "linux":"gnome-terminal",         "darwin":"open -a Terminal"},
    "cmd":          {"win":"start cmd",   "linux":"gnome-terminal",         "darwin":"open -a Terminal"},
    "file manager": {"win":"explorer",    "linux":"nautilus",               "darwin":"open ~"},
    "explorer":     {"win":"explorer",    "linux":"nautilus",               "darwin":"open ~"},
    "task manager": {"win":"taskmgr",     "linux":"gnome-system-monitor",   "darwin":"open -a 'Activity Monitor'"},
    "word":         {"win":"winword",     "linux":"libreoffice --writer",   "darwin":"open -a 'Microsoft Word'"},
    "excel":        {"win":"excel",       "linux":"libreoffice --calc",     "darwin":"open -a 'Microsoft Excel'"},
    "powerpoint":   {"win":"powerpnt",    "linux":"libreoffice --impress",  "darwin":"open -a 'Microsoft PowerPoint'"},
    "chrome":       {"win":"start chrome","linux":"google-chrome",          "darwin":"open -a 'Google Chrome'"},
    "brave":        {"win":"start brave", "linux":"brave-browser",          "darwin":"open -a 'Brave Browser'"},
    "vlc":          {"win":"vlc",         "linux":"vlc",                    "darwin":"open -a VLC"},
    "spotify app":  {"win":"start spotify","linux":"spotify",               "darwin":"open -a Spotify"},
}

def handle_open(text):
    text = text.replace("open ","").replace("kholo ","").replace("launch ","").replace("chalaao ","").strip()
    for name, url in SITE_MAP.items():
        if name in text: open_url(url); return f"'{name.capitalize()}' khol raha hoon sir! 🌐"
    for name, cmds in APP_MAP.items():
        if name in text:
            cmd = cmds.get(get_platform(), cmds.get("linux",""))
            if cmd: run_cmd(cmd); return f"'{name.capitalize()}' open kar raha hoon sir! 💻"
    if "." in text and " " not in text:
        url = text if text.startswith("http") else "https://"+text
        open_url(url); return f"'{text}' khol raha hoon sir! 🌐"
    return None

def wiki_search(query):
    if not WIKI_OK: return "Wikipedia module install nahi hai sir."
    try: return wikipedia.summary(query.strip(), sentences=3)
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Multiple results mile sir — specify karein: {', '.join(e.options[:3])}"
    except wikipedia.exceptions.PageError:
        return f"'{query}' ke baare mein Wikipedia par kuch nahi mila sir."
    except: return "Wikipedia search mein kuch problem aayi sir."

def get_news():
    if not REQUESTS_OK: return "Requests module install nahi hai sir."
    try:
        import xml.etree.ElementTree as ET
        r = requests.get("https://feeds.bbci.co.uk/news/world/rss.xml", timeout=6, headers={"User-Agent":"Mozilla/5.0"})
        root = ET.fromstring(r.content)
        heads = [i.find("title").text.strip() for i in root.findall(".//item")[:5] if i.find("title") is not None]
        return "📰 Aaj ki top khabrein sir:\n\n" + "\n".join(f"• {h}" for h in heads) if heads else "News nahi mili sir."
    except: return "News fetch nahi ho paya sir."

MOTIVATIONS = [
    "Sir, consistency hi sabse bada superpower hai — roz thoda karo, results khud aayenge! 🚀",
    "Aap har us cheez se zyada capable hain jo aap sochte hain — seriously. 💪",
    "Mushkil waqt hamesha better version banata hai — bas ruko mat. ⚡",
    "Failure sikhata hai, quit karna rokta hai — sahi raaste par ho. 🎯",
    "Kal ka tum aaj ke tum ko thanks karega — bas ek chhota step aaj lo. 🌟",
    "Progress slow ho sakti hai — lekin progress hai toh sab theek hai. 🔥",
    "Dreams bade hone chahiye — aur mehnat unse bhi badi. 💡",
]

JOKES = [
    "Programmer ki wife ne kaha — 'Ek litre doodh lao, ande milein toh dozen lao.' Woh 12 litre doodh le aaya. 😂",
    "Main kabhi nahi bhoolta — mera memory RAM mein hai! 😄",
    "Robot doctor ke paas gaya, bola — 'Java mein pain hai.' Doctor ne kaha — 'Try Python.' 😂",
    "WiFi ka password pooch rahe ho? Pehle rishta toh nikalo! 😄",
    "AI ne job nahi li — AI ne time bachaya taaki tum aur kaam kar sako! 🤖",
    "Programmer so nahi sakta — mind mein infinite loop chal rahi thi. 😅",
    "Google se poochha — 'Mujhe koi dost nahi.' Google ne kaha — '10 tips for making friends' 😂",
    "Coding easy hai — bas ek baar sahi bracket lagna chahiye. Bas ek! 😄",
]

FUN_FACTS = [
    "Honey kabhi kharab nahi hoti — 3000 saal purani honey bhi khaane yogya hoti hai! 🍯",
    "Octopus ke 3 hearts hote hain aur unka khoon blue hota hai. 🐙",
    "Bananas technically berries hain — lekin strawberries nahi hain! 🍌",
    "Ek din mein aap average 70,000 thoughts sochte hain. 🧠",
    "Sharks dinosaurs se bhi purani hain — 450 million saal pehle se! 🦈",
]

def detect_intent(t):
    t = t.lower().strip()
    if any(k in t for k in ["kitne baje","what time","time kya","samay kya","time batao"]) or t in ["time","samay","time?"]: return "time"
    if any(k in t for k in ["aaj ki date","what date","kaunsa din","today's date","aaj kaun sa din","date batao"]) or t in ["aaj kya hai","aaj kaun sa din hai"]: return "date"
    if t.startswith("play ") or t.startswith("chalao ") or (("youtube" in t or "song" in t) and ("play" in t or "chala" in t)): return "youtube"
    if t.startswith(("search ","google ","dhundo ","khojo ","search kar ")): return "search"
    if any(t.startswith(p) for p in ["who is ","what is ","wikipedia ","kaun hai ","kya hai ","batao ","tell me about ","explain ","who was ","what was ","kaun tha ","kya hota hai "]): return "wiki"
    if t.startswith(("open ","kholo ","launch ","chalaao ","start ")): return "open"
    if any(k in t for k in ["news","khabar","headlines","aaj ki news","latest news"]): return "news"
    if any(k in t for k in ["weather","mausam","temperature","baarish","garmi","sardi","aaj ka mausam"]): return "weather"
    if any(k in t for k in ["motivate me","motivation do","inspire me","himmat do","hausla do","motivate karo","give me motivation"]): return "motivate"
    if any(k in t for k in ["joke","chutkula","hasao","funny","jokes sunao","ek joke"]): return "joke"
    if any(k in t for k in ["fun fact","interesting fact","kuch interesting","did you know"]): return "funfact"
    if any(k in t for k in ["shutdown","band karo pc","pc band karo","pc off karo"]): return "shutdown"
    if any(k in t for k in ["restart","reboot","dobara chalu karo"]): return "restart"
    if "cancel shutdown" in t or "shutdown cancel" in t: return "cancel_shutdown"
    if any(k in t for k in ["volume up","awaaz badhao","louder","volume badha"]): return "volume_up"
    if any(k in t for k in ["volume down","awaaz kam karo","quieter","volume kam"]): return "volume_down"
    if any(k in t for k in ["mute","awaaz band karo","chup karo system"]): return "mute"
    if any(k in t for k in ["screenshot","screen capture","screen le lo"]): return "screenshot"
    if any(k in t for k in ["meri yaadein","my memories","mere baare mein kya jaante","what do you know about me","show memories"]): return "memory"
    if any(k in t for k in ["clear memory","memory clear karo","sab bhool jao","history delete","memory delete"]): return "clear_memory"
    if any(k in t for k in ["calculate","kitna hoga","calculator","math"]): return "calculator"
    if any(k in t for k in ["system info","pc info","computer info"]): return "sysinfo"
    return "ai"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/command", methods=["POST"])
def command():
    global chat_session
    data = request.get_json() or {}
    raw  = data.get("text","").strip()
    t    = raw.lower().strip()
    if not t: return jsonify({"reply":"Kuch suna nahi sir, dobara bolein."})

    intent = detect_intent(t)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Intent: {intent} | Text: {raw[:50]}")

    if intent == "time":
        return jsonify({"reply": f"Abhi {datetime.datetime.now().strftime('%I:%M:%S %p')} ho raha hai sir. ⏰"})
    if intent == "date":
        return jsonify({"reply": f"Aaj {datetime.datetime.now().strftime('%A, %d %B %Y')} hai sir. 📅"})
    if intent == "youtube":
        song = t.replace("play","").replace("chalao","").replace("youtube","").replace("song","").replace("lagao","").replace("chala","").strip()
        if not song: return jsonify({"reply":"Kaunsa gaana sir? 🎵"})
        url = f"https://www.youtube.com/results?search_query={song.replace(' ','+')}"
        return jsonify({"reply":f"'{song.title()}' chala raha hoon! 🎵","action":"open_url","url":url})
    if intent == "search":
        q = t.replace("search","").replace("google","").replace("dhundo","").replace("khojo","").replace("search kar","").strip()
        if not q: return jsonify({"reply":"Kya search karein sir?"})
        url = f"https://www.google.com/search?q={q.replace(' ','+')}"
        return jsonify({"reply":f"'{q}' search kar raha hoon! 🔍","action":"open_url","url":url})
    if intent == "wiki":
        q = (t.replace("who is","").replace("what is","").replace("wikipedia","")
              .replace("kaun hai","").replace("kya hai","").replace("batao","")
              .replace("tell me about","").replace("explain","").replace("who was","")
              .replace("what was","").replace("kaun tha","").replace("kya hota hai","").strip())
        if not q: return jsonify({"reply":"Kiske baare mein sir?"})
        return jsonify({"reply":wiki_search(q)})
    if intent == "open":
        result = handle_open(t)
        if result: return jsonify({"reply":result})
    if intent == "news": return jsonify({"reply":get_news()})
    if intent == "weather":
        return jsonify({"reply":"Sir, Google par weather khol raha hoon! 🌤️","action":"open_url","url":"https://www.google.com/search?q=weather+today"})
    if intent == "motivate": return jsonify({"reply":random.choice(MOTIVATIONS)})
    if intent == "joke":     return jsonify({"reply":random.choice(JOKES)})
    if intent == "funfact":  return jsonify({"reply":random.choice(FUN_FACTS)})
    if intent == "shutdown":
        run_cmd("shutdown /s /t 5" if get_platform()=="win" else "shutdown -h now")
        return jsonify({"reply":"PC 5 second mein shutdown sir! 🔴"})
    if intent == "restart":
        run_cmd("shutdown /r /t 5" if get_platform()=="win" else "reboot")
        return jsonify({"reply":"PC restart ho raha hai sir! 🔄"})
    if intent == "cancel_shutdown":
        run_cmd("shutdown /a"); return jsonify({"reply":"Shutdown cancel sir! ✅"})
    if intent == "volume_up":
        if get_platform()=="win": run_cmd("nircmd.exe changesysvolume 5000")
        return jsonify({"reply":"Awaaz badha di sir! 🔊"})
    if intent == "volume_down":
        if get_platform()=="win": run_cmd("nircmd.exe changesysvolume -5000")
        return jsonify({"reply":"Awaaz kam kar di sir! 🔉"})
    if intent == "mute":
        if get_platform()=="win": run_cmd("nircmd.exe mutesysvolume 1")
        return jsonify({"reply":"Mute sir! 🔇"})
    if intent == "screenshot":
        if get_platform()=="win": run_cmd("snippingtool")
        return jsonify({"reply":"Screenshot tool sir! 📸"})
    if intent == "memory":
        facts   = get_all_facts()
        history = get_recent_history(8)
        total   = get_memory_count()
        reply   = f"🧠 Mujhe ye sab pata hai sir (Total: {total} conversations):\n\n"
        if facts:
            reply += "📌 Permanent Facts:\n"
            for k,v in facts: reply += f"  • {k}: {v}\n"
            reply += "\n"
        if history:
            reply += "💬 Recent Baatein:\n"
            for role,content in history:
                reply += f"  • {'Aap' if role=='user' else 'Maine'}: {content[:60]}{'...' if len(content)>60 else ''}\n"
        if not facts and not history:
            reply = "Abhi koi memory nahi sir. Baat karo — yaad rakhunga! 🧠"
        return jsonify({"reply":reply})
    if intent == "clear_memory":
        with db_lock:
            cursor.execute("DELETE FROM memory")
            cursor.execute("DELETE FROM facts")
            cursor.execute("DELETE FROM reminders")
            conn.commit()
        chat_session = gemini_model.start_chat(history=[])
        return jsonify({"reply":"Sab clear sir! Fresh start. 🗑️"})
    if intent == "calculator":
        if get_platform()=="win": run_cmd("calc")
        elif get_platform()=="linux": run_cmd("gnome-calculator")
        elif get_platform()=="darwin": run_cmd("open -a Calculator")
        return jsonify({"reply":"Calculator khol raha hoon sir! 🧮"})
    if intent == "sysinfo":
        import platform
        return jsonify({"reply": f"💻 System Info:\n  • OS: {platform.system()} {platform.release()}\n  • Machine: {platform.machine()}\n  • Python: {platform.python_version()}"})

    return jsonify({"reply":ai_reply(raw)})

if __name__ == "__main__":
    print("\n"+"═"*55)
    print("   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗")
    print("   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝")
    print("   ██║███████║██████╔╝██║   ██║██║███████╗")
    print("   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║")
    print("   ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║")
    print("   ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝")
    print("═"*55)
    print(f"  Gemini AI  : ✓ gemini-1.5-pro (UPGRADED!)")
    print(f"  API Key    : ✓ .env se load — SAFE!")
    print(f"  Wikipedia  : {'✓ Ready' if WIKI_OK else '✗  pip install wikipedia'}")
    print(f"  Requests   : {'✓ Ready' if REQUESTS_OK else '✗  pip install requests'}")
    print(f"  Memory DB  : ✓ Persistent (restart-safe)")
    print(f"  Server     : http://localhost:5000")
    print("═"*55+"\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)