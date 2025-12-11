import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import whisper
import torch
import gradio as gr
import os
import time

# --- CONFIGURATION ---
# Use MPS (GPU) to leverage the M3 Pro chip
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
MODEL_SIZE = "medium"

print(f"🚀 Starting on device: {DEVICE.upper()}")
print(f"📥 Loading model '{MODEL_SIZE}'...")

model = whisper.load_model(MODEL_SIZE, device=DEVICE)

# --- PROCESSING FUNCTION (AUTO DETECT MODE) ---
def transcribe_audio(file_path):
    if file_path is None:
        return "⚠️ Please upload a file or record audio!"
    
    print(f"🔄 Processing file: {file_path} (Auto Detect Mode)")
    
    # model.transcribe defaults to Auto Detect Language if 'language' parameter is omitted
    # task="translate" -> Forces translation into English
    # fp16=False -> Prevents precision errors on Mac MPS
    result = model.transcribe(file_path, task="translate", fp16=False)
    
    text = result["text"]
    
    # Save result to file
    save_name = f"Result_English_{int(time.time())}.txt"
    with open(save_name, "w", encoding="utf-8") as f:
        f.write(text)
        
    return text

# --- MINIMALIST INTERFACE ---
# REMOVED 'allow_flagging' to prevent TypeError
app = gr.Interface(
    fn=transcribe_audio,
    inputs=gr.Audio(type="filepath", label="Upload File or Record Audio (Vietnamese/Chinese/English...)"),
    outputs=gr.Textbox(label="Result (English Translation)"),
    title="Whisper Auto Translator",
    description="Automatically detects input language and translates to English."
)

if __name__ == "__main__":
    app.launch()