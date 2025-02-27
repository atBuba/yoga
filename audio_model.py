from flask import Flask, request, jsonify
import torch
import re
from ctc_forced_aligner import (
    load_audio,
    load_alignment_model,
    generate_emissions,
    preprocess_text,
    get_alignments,
    get_spans,
    postprocess_results,
)
import demucs.separate
import os
import shutil
import torchaudio.functional as F

# Создаем Flask-приложение
app = Flask(__name__)

# Глобальные переменные для модели
alignment_model = None
alignment_tokenizer = None

def initialize_model():
    global alignment_model, alignment_tokenizer
    # device = "cuda" if torch.cuda.is_available() else "cpu"
    device = "cuda"
    dtype = torch.float32 if device == "cuda" else torch.float32
    alignment_model, alignment_tokenizer = load_alignment_model(device, dtype=dtype)

# Инициализируем модель при запуске сервера
initialize_model()

@app.route("/align", methods=["POST"])
def align_audio_text():
    try:
        # Получаем файлы из запроса
        data = request.get_json()
        audio_path = data.get("audio_path")
        text_path = data.get("text_path")
        language = data.get("language", "iso")
        print(audio_path, text_path, language)

        demucs.separate.main([
            "--mp3", "--two-stems", "vocals",
            "-n", "mdx_extra_q",
            "--overlap", "0.8",
            "--shifts", "3",
            "--device", "cuda",
            audio_path
        ])

        
        # Пути к входным и выходным файлам
        output_folder = "separated/mdx_extra_q/mp3_file"
        static_folder = "static"
        
        # Создание папки static, если её нет
        os.makedirs(static_folder, exist_ok=True)
        
        # Перемещение файлов
        shutil.move(os.path.join(output_folder, "vocals.mp3"), os.path.join(static_folder, "vocal.mp3"))
        shutil.move(os.path.join(output_folder, "no_vocals.mp3"), os.path.join(static_folder, "no_vocal.mp3"))

        vocal_path = 'static/vocal.mp3'
        no_vocal_path = 'static/no_vocal.mp3'
        


        # Загружаем аудио и текст
        audio_waveform = load_audio(vocal_path, alignment_model.dtype, alignment_model.device)

        audio_waveform = F.gain(audio_waveform, gain_db=40.0)  # Увеличиваем громкость на 5 dB
        
        with open(text_path, "r", encoding="utf-8") as f:
            text = f.read().replace("\n", " ").strip()
            text = re.sub(r'\[.*?\]', '', text).strip()

        # Генерация эмиссий
        batch_size = 16
        emissions, stride = generate_emissions(
            alignment_model, audio_waveform, batch_size=batch_size
        )

        # Предобработка текста
        tokens_starred, text_starred = preprocess_text(
            text,
            romanize=True,
            language='rus',
        )

        # Получение выравниваний
        segments, scores, blank_token = get_alignments(
            emissions,
            tokens_starred,
            alignment_tokenizer,
        )

        # Получение временных промежутков для слов
        spans = get_spans(tokens_starred, segments, blank_token)


        
        # Постобработка результатов
        word_timestamps = postprocess_results(text_starred, spans, stride, scores)
        # Возвращаем результат
        return jsonify({"word_timestamps": word_timestamps})

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)