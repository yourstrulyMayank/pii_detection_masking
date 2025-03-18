"""
Title: Audio PII Masking
Author: Mayank Harlalka
Date: 05-10-2024
Description: Detects PII in speech transcription, and masks it in the text. It accepts an audio path and return the masked audio text.
"""

# Import necessary libraries
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from gliner import GLiNER
import spacy
import sys
from common_functions import redact_pii
from text import main
import whisper
import subprocess
import ffmpeg
import os
import sys

# Define the relative path to FFmpeg bin
ffmpeg_relative_path = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin")

# Add FFmpeg to system PATH
os.environ["PATH"] = ffmpeg_relative_path + os.pathsep + os.environ["PATH"]

# Verify FFmpeg installation
os.system("ffmpeg -version")

# Main function to handle audio file input
def main(audio_file_path, labels, model):
    # Load GLiNER model for PII detection
    ## Try to download it in setup.sh
    

    # nlp = spacy.load('en_core_web_lg')
    nlp = spacy.load('en_core_web_sm')

    # Setup device and model for automatic speech recognition (ASR)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    # Try to download it in setup.sh
    # audio_model_id = "openai/whisper-large-v3"
    # audio_model_id = "openai/whisper-small"
    
    audio_model_path = "./models/whisper-small"
    print('Model load started')
    try:
        subprocess.run(["ffmpeg", "-version"], check=True)
        print("FFmpeg is installed and working!")
    except FileNotFoundError:
        print("Error: FFmpeg is not found. Ensure it’s installed and in PATH.")
    whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained(
        audio_model_path, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
        )
    whisper_model.to(device)

    # # Initialize processor and ASR pipeline
    processor = AutoProcessor.from_pretrained(audio_model_path)
    # Load Whisper model for speech-to-text
    # whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained(
        # audio_model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    # )
    # whisper_model.to(device)

    # Initialize processor and ASR pipeline
    # processor = AutoProcessor.from_pretrained(audio_model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=whisper_model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=10,
        batch_size=2,
        return_timestamps=True,
        torch_dtype=torch_dtype,
        device=device,
    )

    # Transcribe audio using Whisper pipeline
    result = pipe(audio_file_path)
    print('Model loaded')
    transcribed_text = result['text']

    
    
    # Redact any PII from the transcribed text
    redacted_text = redact_pii(transcribed_text, labels, model)
    
    return redacted_text



def process_audio(file_path, labels):
    # Placeholder: Simulating audio transcription
    transcription = "This is a simulated transcription of the audio file."
    masked_text = main(transcription, labels)
    return transcription, masked_text


if __name__ == "__main__":
    try:
        # Path to the audio file
        sample_audio = 'path'    
        labels = ["work", "booking number", "personally identifiable information", "credit card number", "CVV","social security number", "driver licence", "book", "full address", "company", "actor", "character","email", "passport number", "Social Security Number", "phone number"]    
        # Run the main function to get the redacted text from the audio transcription
        redacted_output = main(sample_audio, labels)
        print("Redacted Text:\n", redacted_output)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
