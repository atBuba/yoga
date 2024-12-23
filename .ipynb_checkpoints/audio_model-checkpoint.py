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

# Создаем Flask-приложение
app = Flask(__name__)

# Глобальные переменные для модели
alignment_model = None
alignment_tokenizer = None

def initialize_model():
    global alignment_model, alignment_tokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
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

        # Загружаем аудио и текст
        audio_waveform = load_audio(audio_path, alignment_model.dtype, alignment_model.device)
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
            language=language,
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
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
