# setup.sh
pip install -r requirements.txt
pip install git+https://github.com/JaidedAI/EasyOCR.git
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_lg
huggingface-cli download urchade/gliner_multi_pii-v1
huggingface-cli download openai/whisper-large-v3
