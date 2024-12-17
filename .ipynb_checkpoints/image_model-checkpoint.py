from flask import Flask, request, jsonify
from PIL import Image
import os
import io
import torch
import requests
from diffusers import FluxPipeline
from huggingface_hub import login

API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
headers = {"Authorization": "Bearer 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"}

login(token="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")

app = Flask(__name__)

# Настройка папки для сохранения изображений
STATIC_FOLDER = os.path.join(os.getcwd(), "static")
os.makedirs(STATIC_FOLDER, exist_ok=True)

#Загрузка модели
print("Загрузка модели...")
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to('cuda')
pipe.enable_model_cpu_offload()  # Экономия VRAM, если GPU ограничен
print("Модель загружена.")

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.content


@app.route("/generate", methods=["POST"])
def generate():
    """Генерация изображения на основе запроса."""
    data = request.json
    prompt = data.get("prompt", "Default prompt")
    seed = data.get("seed", 0)
    height = data.get("height", 480)
    width = data.get("width", 848)
    guidance_scale = data.get("guidance_scale", 3.5)
    num_inference_steps = data.get("num_inference_steps", 25)

    try:
        generator = torch.Generator("cuda").manual_seed(seed)
        image = pipe(
            prompt=prompt,
            height=height,
            width=width,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            generator=generator
        ).images[0]

        filename = f"generate_image_{seed}.png"
        file_path = os.path.join(STATIC_FOLDER, filename)
        image.save(file_path)

        # Генерация изображения
        # image_bytes = query({
        #     "inputs": prompt,
        #     "parameters": {
        #         "seed": seed,
        #         "height": height,
        #         "width": width, 
        #         "guidance_scale": guidance_scale
        #     }
        # })

        # image = Image.open(io.BytesIO(image_bytes))
        # # Сохранение изображения
        # filename = f"generate_image_{seed}.png"
        # file_path = os.path.join(STATIC_FOLDER, filename)
        # image.save(file_path)

        return jsonify({
            "success": True,
            "image_url": f"static/{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, use_reloader=False, debug=True)
