from fastapi import FastAPI,UploadFile,File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from Web import main
import os
from google import genai
from google.genai import types
import io
app = FastAPI()
origin = [
        "http://localhost:5173",
        "https://ai-agentic-desktop-assistant.vercel.app/",
        "https://ai-agentic-desktop-assistant.onrender.com",
]
app.add_middleware(
        CORSMiddleware,
        allow_origins = ["*"],
        allow_credentials=True,
        allow_headers =["*"],
        allow_methods = ["*"]
)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
class Root_Message(BaseModel):
        user_input : str

app.mount("/assets",StaticFiles(directory="dist/assets",html=True),name="assets")



@app.get("/")



def serve():
        return FileResponse("dist/index.html")


@app.get("/{path : path}")



async def catch_all(path : str):
        return FileResponse("dist/index.html")



@app.get("/")
async def root():
        return {
                "message" : "hi"
        }


@app.post("/audio")
async def audio(audio : UploadFile = File(...)):
        audio_bytes = await audio.read()
        audio_part = types.Part.from_bytes(
                data=audio_bytes,
                mime_type=audio.content_type
        )
        response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[
                        audio_part,
                        "Provide a clean text transcription of this audio data."
                ]
        )
        try:
                msg = response.text
                print(msg)
                if msg!="":
                        bot_response = main(msg)
                        print(f"bot msg : {bot_response}")
                return {
                                "message" : "recieved",
                                "bot_msg" : bot_response["msg"],
                                "url" : bot_response["url"],
                                "user_txt" : msg
                        }
        except Exception as e:
                return {
                        "message" : "recieved",
                        "bot_msg" : bot_response["msg"],
                        "url" : "not open"
                }


@app.post("/usermsg")
async def root_post(data : dict):
        try:
                msg = data["user_msg"]
                print(msg)
                if msg!="":
                        bot_response = main(msg)
                        print(f"bot msg : {bot_response}")
                return {
                                "message" : "recieved",
                                "bot_msg" : bot_response["msg"],
                                "url" : bot_response["url"]
                        }
        except Exception as e:
                return {
                        "message" : "recieved",
                        "bot_msg" : bot_response["msg"],
                        "url" : "not open"
                }