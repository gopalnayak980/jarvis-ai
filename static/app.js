// ── Elements ──────────────────────────────────────────────────────────────
const micBtn       = document.getElementById("micBtn");
const textInput    = document.getElementById("textInput");
const sendBtn      = document.getElementById("sendBtn");
const chatWindow   = document.getElementById("chatWindow");
const liveText     = document.getElementById("liveText");
const transcriptBar= document.getElementById("transcriptBar");
const avatarCore   = document.getElementById("avatarCore");
const avatarPulse  = document.getElementById("avatarPulse");
const aiMouth      = document.getElementById("aiMouth");
const jarvisTagline= document.getElementById("jarvisTagline");
const statusLabel  = document.getElementById("statusLabel");
const eyeL         = document.getElementById("eyeL");
const eyeR         = document.getElementById("eyeR");
const voiceBars    = document.getElementById("voiceBars");
const micWaves     = document.getElementById("micWaves");
const memoryList   = document.getElementById("memoryList");
const moodLabel    = document.getElementById("moodLabel");
const moodIcon     = document.querySelector(".mood-icon");

const BACKEND = "https://jarvis-ai-8zh0.onrender.com/api/command";

let listening = false;
let speaking  = false;
let msgCount  = 0;
let recognition = null;
const memories  = [];

// ── Particles ──────────────────────────────────────────────────────────────
(function () {
  const canvas = document.getElementById("particleCanvas");
  const ctx = canvas.getContext("2d");
  let W, H;
  const pts = [];

  function resize() { W = canvas.width = innerWidth; H = canvas.height = innerHeight; }
  resize(); window.addEventListener("resize", resize);

  for (let i = 0; i < 70; i++) pts.push({
    x: Math.random() * innerWidth, y: Math.random() * innerHeight,
    r: Math.random() * 1.1 + 0.2,
    dx: (Math.random() - 0.5) * 0.25, dy: (Math.random() - 0.5) * 0.25,
    a: Math.random() * 0.35 + 0.05
  });

  function draw() {
    ctx.clearRect(0, 0, W, H);
    pts.forEach(p => {
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,212,255,${p.a})`; ctx.fill();
      p.x += p.dx; p.y += p.dy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// ── Clock ──────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById("sysTime").textContent =
    now.toLocaleTimeString("en-IN", { hour12: false });
  document.getElementById("sysDate").textContent =
    now.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}
setInterval(updateClock, 1000); updateClock();

// ── Simulated System Stats ─────────────────────────────────────────────────
const cpuHistory = [], ramHistory = [], netHistory = [];

function randomBetween(a, b) { return Math.random() * (b - a) + a; }

function updateRing(ringId, pctId, val) {
  const circ = 150.8;
  document.getElementById(ringId).style.strokeDashoffset = circ - (val / 100) * circ;
  document.getElementById(pctId).textContent = Math.round(val) + "%";
}

function buildSpark(id, history) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = "";
  const max = Math.max(...history, 1);
  history.forEach(v => {
    const bar = document.createElement("div");
    bar.className = "spark-bar";
    bar.style.height = (v / max * 26) + "px";
    el.appendChild(bar);
  });
}

function updateStats() {
  const cpu = randomBetween(10, 60);
  const ram = randomBetween(30, 75);
  const up  = randomBetween(1, 20);
  const down= randomBetween(2, 30);

  cpuHistory.push(cpu); if (cpuHistory.length > 12) cpuHistory.shift();
  ramHistory.push(ram); if (ramHistory.length > 12) ramHistory.shift();
  netHistory.push(up + down); if (netHistory.length > 12) netHistory.shift();

  updateRing("cpuRing", "cpuPct", cpu);
  updateRing("ramRing", "ramPct", ram);
  document.getElementById("cpuVal").textContent = Math.round(cpu) + "%";
  document.getElementById("ramVal").textContent = Math.round(ram) + "%";
  document.getElementById("netUp").textContent   = up.toFixed(1);
  document.getElementById("netDown").textContent = down.toFixed(1);

  buildSpark("cpuSpark", cpuHistory);
  buildSpark("ramSpark", ramHistory);
  buildSpark("netSpark", netHistory);
}
setInterval(updateStats, 2000); updateStats();

// Battery API
if (navigator.getBattery) {
  navigator.getBattery().then(bat => {
    function updateBat() {
      const pct = Math.round(bat.level * 100);
      document.getElementById("batPct").textContent = pct + "%";
      document.getElementById("batFill").style.width = pct + "%";
      document.getElementById("batStatus").textContent = bat.charging ? "Charging..." : "On battery";
      document.getElementById("batFill").style.background =
        pct < 20 ? "#ff3c5a" : pct < 50 ? "#ffb800" : "var(--c3)";
    }
    updateBat();
    bat.addEventListener("levelchange", updateBat);
    bat.addEventListener("chargingchange", updateBat);
  });
}

// ── Weather ────────────────────────────────────────────────────────────────
function loadWeather() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(pos => {
    const { latitude: lat, longitude: lon } = pos.coords;
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true&hourly=relativehumidity_2m,apparent_temperature,windspeed_10m`;
    fetch(url).then(r => r.json()).then(data => {
      const cw = data.current_weather;
      const temp = Math.round(cw.temperature);
      const wind = Math.round(cw.windspeed);
      const code = cw.weathercode;
      const icon = code <= 1 ? "☀️" : code <= 3 ? "⛅" : code <= 51 ? "🌦" : code <= 67 ? "🌧" : code <= 77 ? "❄️" : "⛈";
      const desc = code <= 1 ? "Clear Sky" : code <= 3 ? "Partly Cloudy" : code <= 51 ? "Drizzle" : code <= 67 ? "Rainy" : "Stormy";

      document.getElementById("weatherTemp").textContent = temp + "°C";
      document.getElementById("weatherIcon").textContent = icon;
      document.getElementById("weatherDesc").textContent = desc;
      document.getElementById("weatherWind").textContent = wind + " km/h";

      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`)
        .then(r => r.json())
        .then(geo => {
          const city = geo.address.city || geo.address.town || geo.address.village || "";
          const state = geo.address.state || "";
          document.getElementById("weatherLoc").textContent = `📍 ${city}, ${state}`;
        }).catch(() => {});
    }).catch(() => {});
  }, () => {
    document.getElementById("weatherDesc").textContent = "Location access denied";
  });
}
loadWeather();

// ── Avatar Blink ───────────────────────────────────────────────────────────
function blink() {
  [eyeL, eyeR].forEach(e => e.classList.add("blink"));
  setTimeout(() => [eyeL, eyeR].forEach(e => e.classList.remove("blink")), 130);
}
setInterval(() => { if (!speaking) blink(); }, 3200 + Math.random() * 2000);

// ── Avatar States ──────────────────────────────────────────────────────────
const moods = {
  idle:      { icon: "😊", label: "Happy",    color: "var(--c3)" },
  listening: { icon: "👂", label: "Listening", color: "var(--c3)" },
  thinking:  { icon: "🤔", label: "Thinking",  color: "var(--c1)" },
  speaking:  { icon: "🗣️", label: "Speaking",  color: "var(--c1)" },
};

function setAvatarState(state) {
  avatarCore.className = "avatar-core";
  avatarPulse.className = "avatar-pulse";
  voiceBars.classList.remove("active");

  const mood = moods[state] || moods.idle;
  moodIcon.textContent = mood.icon;
  moodLabel.textContent = mood.label;
  moodLabel.style.color = mood.color;

  if (state === "listening") {
    avatarCore.classList.add("listening");
    avatarPulse.classList.add("active");
    voiceBars.classList.add("active");
  } else if (state === "speaking") {
    avatarCore.classList.add("speaking");
    avatarPulse.classList.add("active");
  }
}

// ══════════════════════════════════════════════════════════════
// ── UPGRADED VOICE SYSTEM ─────────────────────────────────────
// ══════════════════════════════════════════════════════════════

// Voice cache — load once, use always
let allVoices = [];
let voicesLoaded = false;

// Load voices as soon as possible
function loadVoices() {
  allVoices = window.speechSynthesis.getVoices();
  if (allVoices.length > 0) {
    voicesLoaded = true;
    console.log(`✓ ${allVoices.length} voices loaded`);
  }
}

// Voices load async in browsers — handle both cases
loadVoices();
window.speechSynthesis.onvoiceschanged = () => {
  loadVoices();
};

// ── Smart Voice Selector ──────────────────────────────────────
function getBestVoice(isHindi) {
  if (!voicesLoaded) loadVoices();

  if (isHindi) {
    // Priority order for Hindi voices
    const hindiPriority = [
      "Google हिन्दी",
      "Microsoft Swara",
      "Microsoft Hemant",
      "hi-IN",
      "hi_IN",
    ];
    for (const name of hindiPriority) {
      const v = allVoices.find(v =>
        v.name.includes(name) || v.lang === name || v.lang === "hi-IN"
      );
      if (v) {
        console.log(`✓ Hindi voice: ${v.name}`);
        return v;
      }
    }
    // Fallback — any Hindi voice
    return allVoices.find(v => v.lang.startsWith("hi")) || null;

  } else {
    // Priority order for English voices — most natural ones first
    const englishPriority = [
      "Google UK English Female",  // Best female voice
      "Google UK English Male",    // Best male voice
      "Microsoft Zira",            // Windows natural female
      "Microsoft Mark",            // Windows natural male
      "Microsoft David",           // Windows classic
      "Google US English",         // US English
      "Samantha",                  // macOS natural
      "Daniel",                    // macOS UK
      "Karen",                     // macOS AU
      "en-IN",                     // Indian English
    ];
    for (const name of englishPriority) {
      const v = allVoices.find(v =>
        v.name.includes(name) || v.lang === name
      );
      if (v) {
        console.log(`✓ English voice: ${v.name}`);
        return v;
      }
    }
    // Fallback — any English voice
    return allVoices.find(v => v.lang.startsWith("en")) ||
           allVoices[0] ||
           null;
  }
}

// ── Upgraded speakText ────────────────────────────────────────
function speakText(text) {
  if (!text || !text.trim()) return;
  if (!('speechSynthesis' in window)) {
    setAvatarState("idle");
    return;
  }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  speaking = true;
  setAvatarState("speaking");

  // Detect language
  const isHindi = /[\u0900-\u097F]/.test(text);

  const u = new SpeechSynthesisUtterance(text);

  // Set language
  u.lang = isHindi ? "hi-IN" : "en-GB";

  // Get best voice
  const voice = getBestVoice(isHindi);
  if (voice) u.voice = voice;

  // Fine-tuned settings for most natural sound
  if (isHindi) {
    u.pitch  = 1.0;   // natural pitch
    u.rate   = 0.82;  // slightly slow — clear Hindi
    u.volume = 1.0;
  } else {
    u.pitch  = 0.9;   // slightly deeper — more like Jarvis
    u.rate   = 0.85;  // calm, authoritative pace
    u.volume = 1.0;
  }

  u.onstart = () => {
    speaking = true;
    setAvatarState("speaking");
  };

  u.onend = () => {
    speaking = false;
    setAvatarState("idle");
  };

  u.onerror = (e) => {
    console.warn("Speech error:", e.error);
    speaking = false;
    setAvatarState("idle");
  };

  // Small delay ensures voice is ready
  setTimeout(() => {
    window.speechSynthesis.speak(u);
  }, 100);
}

// ── Fix Chrome TTS bug (stops after ~15 seconds) ─────────────
// Chrome has a bug where long speech stops after 15s
// This keeps it alive
setInterval(() => {
  if (speaking && window.speechSynthesis.speaking) {
    window.speechSynthesis.resume();
  }
}, 10000);

// ══════════════════════════════════════════════════════════════

// ── Speech Recognition ─────────────────────────────────────────────────────
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.lang = "en-IN";

  recognition.onstart = () => {
    listening = true;
    micBtn.classList.add("listening");
    transcriptBar.classList.add("active");
    liveText.textContent = "Sun raha hoon...";
    liveText.classList.add("active");
    setAvatarState("listening");
  };

  recognition.onresult = (e) => {
    let final = "", interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      e.results[i].isFinal ? (final += t) : (interim += t);
    }
    const cur = final || interim;
    textInput.value = cur;
    liveText.textContent = cur || "Sun raha hoon...";
    if (final.trim() && !speaking) { recognition.stop(); sendCommand(final.trim()); }
  };

  recognition.onerror = (e) => {
    listening = false;
    micBtn.classList.remove("listening");
    transcriptBar.classList.remove("active");
    liveText.textContent = "Mic error: " + e.error;
    liveText.classList.remove("active");
    setAvatarState("idle");
  };

  recognition.onend = () => {
    listening = false;
    micBtn.classList.remove("listening");
    transcriptBar.classList.remove("active");
    liveText.textContent = "Kuch bolo ya type karo...";
    liveText.classList.remove("active");
    if (!speaking) setAvatarState("idle");
  };
}

// ── Typewriter ─────────────────────────────────────────────────────────────
function typewriter(el, text, onDone) {
  let i = 0;
  el.textContent = "";
  setAvatarState("speaking");
  const iv = setInterval(() => {
    el.textContent += text[i++];
    chatWindow.scrollTop = chatWindow.scrollHeight;
    if (i >= text.length) { clearInterval(iv); if (onDone) onDone(); }
  }, 22);
}

// ── Add Message ────────────────────────────────────────────────────────────
function addMsg(who, text, doTypewriter = false) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${who}`;
  const now = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  wrap.innerHTML = `
    <div class="msg-avatar">${who === "jarvis" ? "J" : "U"}</div>
    <div class="msg-content">
      <div class="msg-bubble" id="b-${++msgCount}"></div>
      <div class="msg-time">${now}</div>
    </div>`;
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  const bubble = wrap.querySelector(".msg-bubble");
  if (doTypewriter && who === "jarvis") {
    typewriter(bubble, text, () => speakText(text));
  } else {
    bubble.textContent = text;
    if (who === "jarvis") speakText(text);
  }
  return wrap;
}

function addThinking() {
  const id = "think-" + Date.now();
  const wrap = document.createElement("div");
  wrap.className = "msg jarvis thinking-bubble"; wrap.id = id;
  wrap.innerHTML = `<div class="msg-avatar">J</div><div class="msg-bubble"><div class="dot-anim"></div><div class="dot-anim"></div><div class="dot-anim"></div></div>`;
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return id;
}
function removeMsg(id) { document.getElementById(id)?.remove(); }

// ── Memory panel ───────────────────────────────────────────────────────────
function addMemory(text) {
  const time = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  memories.unshift({ text, time });
  if (memories.length > 6) memories.pop();
  memoryList.innerHTML = memories.map(m => `
    <div class="memory-item">
      <span class="mem-dot"></span>
      <span class="mem-text">${m.text.substring(0, 30)}${m.text.length > 30 ? "..." : ""}</span>
      <span class="mem-time">${m.time}</span>
    </div>`).join("");
}

// ── Send Command ───────────────────────────────────────────────────────────
async function sendCommand(text) {
  if (!text || !text.trim()) return;
  text = text.trim();
  textInput.value = "";

  if (text.toLowerCase().includes("clear chat")) {
    chatWindow.innerHTML = "";
    addMsg("jarvis", "Chat saaf kar diya sir! ✨", true);
    return;
  }

  addMsg("user", text);
  addMemory(text);

  const thinkId = addThinking();
  setAvatarState("thinking");

  try {
    const res  = await fetch(BACKEND, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    removeMsg(thinkId);
    const reply = data.reply || "Koi jawab nahi mila.";
    addMsg("jarvis", reply, true);
    if (data.action === "open_url" && data.url) {
      setTimeout(() => window.open(data.url, "_blank"), 900);
    }
  } catch (err) {
    removeMsg(thinkId);
    addMsg("jarvis", "⚠️ Backend se connect nahi ho pa raha. server.py chal raha hai?", false);
    setAvatarState("idle");
  }
}

// ── Quick commands ─────────────────────────────────────────────────────────
function quickCmd(text) { sendCommand(text); }

// ── Events ─────────────────────────────────────────────────────────────────
micBtn.addEventListener("click", () => {
  if (!recognition) { alert("Chrome/Edge use karein mic ke liye."); return; }
  listening ? recognition.stop() : recognition.start();
});

sendBtn.addEventListener("click", () => {
  const t = textInput.value.trim(); if (t) sendCommand(t);
});

textInput.addEventListener("keydown", e => {
  if (e.key === "Enter") { const t = textInput.value.trim(); if (t) sendCommand(t); }
});

window.addEventListener("keydown", e => {
  if (e.code === "Space" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); micBtn.click(); }
  if (e.code === "Escape") { chatWindow.innerHTML = ""; addMsg("jarvis", "Chat clear kar diya sir!", true); }
});

// ── Boot ───────────────────────────────────────────────────────────────────
setTimeout(() => {
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Suprabhat" : hour < 17 ? "Namaskar" : "Shubh sandhya";
  addMsg("jarvis",
    `${greet}! Main Jarvis hoon — aapka personal AI assistant. Hindi mein bolein ya English mein — dono perfect chalega. Aaj main aapki kya madad kar sakta hoon? 😊`,
    true
  );
}, 900);