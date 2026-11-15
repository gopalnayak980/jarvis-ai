# JARVIS

**Bilingual (Hindi and English) AI voice assistant** with persistent memory, real-time image analysis and a custom animated HUD interface.

**Live demo:** https://jarvis-ai-8zh0.onrender.com

> The app is hosted on a free plan, so the first load may take 30 to 50 seconds to wake up.

## Features

- **Voice interaction** using the Web Speech API for speech recognition and text-to-speech
- **Bilingual:** understands and replies in Hindi and English
- **Persistent memory:** conversations are stored in SQLite and survive server restarts
- **Vision:** real-time image analysis with the Gemini Vision API
- **Motion detection** using the JavaScript Canvas API and WebRTC camera access
- **Custom HUD-style frontend** with animations

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| AI | Google Gemini (text and Vision) |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript, Web Speech API, WebRTC, Canvas API |
| Deployment | Render |

## Run Locally

```bash
git clone https://github.com/gopalnayak980/jarvis-ai.git
cd jarvis-ai

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then add your Gemini API key
python app.py
```

Open http://localhost:5000 in Chrome (best support for the Web Speech API) and allow microphone and camera access.

## Environment Variables

Copy `.env.example` to `.env` and fill in your own value:

```env
GEMINI_API_KEY=
```

## Author

**Gopal Nayak** · [Portfolio](https://gopalnayak980.github.io/gopal-portfolio) · [LinkedIn](https://www.linkedin.com/in/gopalnayak2005)

## License

MIT
