import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from google import genai

app = FastAPI()

YEMOT_API_URL = "https://www.call2all.co.il/ym/api"

@app.api_route("/ai-talk", methods=["GET", "POST"])
async def ai_talk(request: Request):
    form = await request.form()
    
    # בדיקה האם ימות המשיח שלחה קובץ קול (כלומר, המשתמש סיים לדבר והקיש #)
    voice_file = None
    for key in form:
        if hasattr(form[key], "filename") and form[key].filename:
            voice_file = form[key]
            break

    # שלב א': אם עדיין אין קובץ קול (כניסה ראשונית לשלוחה)
    # אנחנו מורים לימות המשיח להתחיל להקליט מיד בשקט, ולסגור על # או 3 שניות שקט
    if not voice_file:
        return PlainTextResponse("read=,VoiceFile,s=3,s_mode=record")

    # שלב ב': הגיע קובץ קול! מעבדים אותו מול Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return PlainTextResponse("text=שגיאה, מפתח API חסר.\nhangup=yes")

    client = genai.Client(api_key=api_key)

    file_bytes = await voice_file.read()
    temp_filename = "temp_user_audio.wav"
    with open(temp_filename, "wb") as f:
        f.write(file_bytes)

    ai_reply_text = "לא הצלחתי לעבד את התשובה."
    try:
        audio_file_ref = client.files.upload(file=temp_filename)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                audio_file_ref,
                "אתה עוזר קולי חכם. ענה בעברית בצורה קצרה וברורה (משפט אחד או שניים)."
            ]
        )
        ai_reply_text = response.text if response.text else "לא התקבלה תשובה מהמודל."
    except Exception as e:
        ai_reply_text = "אירעה שגיאה בעיבוד הקול."
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    # שלב ג': שליחת התשובה למערכת היעד (0747277229, סיסמה 330682675, שלוחה 3)
    try:
        login_res = requests.get(f"{YEMOT_API_URL}/Login", params={
            "username": "0747277229",
            "password": "330682675"
        }).json()

        if login_res.get("response") == "OK":
            token = login_res.get("token")
            requests.post(f"{YEMOT_API_URL}/UploadText", data={
                "token": token,
                "path": "3/ai_answer.txt",
                "text": ai_reply_text,
                "append": "no"
            })
    except Exception as api_err:
        print(f"Failed to send to Yemot target system: {api_err}")

    # שלב ד': הודעה למשתמש שהכל בוצע בהצלחה וניתוק
    return PlainTextResponse("text=ההקלטה עובדה ונשלחה בהצלחה ליעד.\nhangup=yes")
