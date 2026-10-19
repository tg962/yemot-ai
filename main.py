import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from google import genai

app = FastAPI()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.post("/ai-talk")
async def ai_talk(VoiceFile: UploadFile = File(None)):
    if not VoiceFile:
        return PlainTextResponse("text=שגיאה בקליטת השמע, נסה שוב. id=1.1")

    file_bytes = await VoiceFile.read()
    temp_filename = "temp_user_audio.wav"
    with open(temp_filename, "wb") as f:
        f.write(file_bytes)

    try:
        audio_file_ref = client.files.upload(file=temp_filename)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                audio_file_ref,
                "אתה עוזר קולי חכם בשיחת טלפון. ענה בעברית בצורה קצרה, טבעית, מתאימה להקראה קולית (עד 2-3 משפטים)."
            ]
        )
        ai_reply_text = response.text
    except Exception as e:
        ai_reply_text = "סליחה, לא הצלחתי להבין. נסה שוב."
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    return PlainTextResponse(f"text={ai_reply_text}\nread=,s=3,s_mode=record")
