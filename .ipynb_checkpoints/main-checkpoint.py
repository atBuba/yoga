import os
import io
import random
import requests
from PIL import Image
from flask import Flask, render_template, request, jsonify
import time
from tools import *
from pathlib import Path
from moviepy.editor import VideoFileClip

# URL микросервиса модели
IMAGE_MODEL_SERVICE_URL = "http://127.0.0.1:5000"

app = Flask(__name__)

def query_model(payload):
    """Запрос к микросервису модели."""
    response = requests.post(f"{IMAGE_MODEL_SERVICE_URL}/generate", json=payload)
    response.raise_for_status()
    return response.json()


@app.route('/create_video', methods=['POST'])
def create_video(image_path, duration):
    seed = random.randint(0, 2**32 - 1)
    height = 480
    width = 848
    num_frames = 121
    frame_rate = 25

    payload = {
        'image_path': image_path,
        'duration': duration
    }

    response = requests.post("http://127.0.0.1:6000/process_images", json=payload)

    if response.status_code == 200:
        video_url = response.json().get('video_url')
        return video_url
    else:
        return None




@app.route('/gallery')
def gallery():
    return render_template('gallery.html')


@app.route('/')
def index():
    return render_template('index.html')
  
@app.route('/show', methods=['POST'])
def show():
    data = request.json
    images = data.get('images', [])
    subtitles = data.get('subtitles', 'false') != 'false'
    font = data['font']
    color = data['color']
    
    # get font and font collor
    font_path = get_font_path(font)
    font_fill_color = get_font_color(color)

    # path to files 
    audio_path = 'static/mp3_file.mp3'
    ttml_file_lines = 'static/ttml_file_lines.ttml'
    ttml_file_words = 'static/ttml_file_words.ttml'

    output_video_avi = 'video/final_video.mp4'
    output_video_mp4 = 'video/final_video_with_audio_1.mp4'

    lyrics_file = 'static/lyrics.txt'

    if check_file_exists(ttml_file_lines) and check_file_exists(ttml_file_words):
        ttml_words = parse(ttml_file=ttml_file_words)
        ttml_two_lines = parse(ttml_file=ttml_file_lines, two_lines=True)
        ttml_lines = parse(ttml_file=ttml_file_lines)
    else: 
        ttml_words = parse(txt_files=lyrics_file, word=True)
        ttml_two_lines = parse(txt_files=lyrics_file, two_lines=True)
        ttml_lines = parse(txt_files=lyrics_file)

    images_folder = ""
    images_path = [os.path.join(images_folder, image) for image in images]
    # duration = 0
    # j = 0
    # imgs = []
    
    # # Create clips based on duration from ttml
    # for image, line in zip(images_path, ttml_two_lines):
    #     j += len(line['text'].split(' '))
    #     imgs.append(ImageClip(image, duration=ttml_words[j]['end'] - duration + 1))
    #     duration = ttml_words[j]['end']


    # create_slideshow(imgs, ttml_words, ttml_lines, font=font_path, font_color=color, output_path = output_video_avi, addSubtitles=subtitles)
    
    duration = 0
    j = 0
    videos = []

    for image_path, line in zip(images_path, ttml_two_lines):   
        j += len(line['text'].split(' '))
        video_url = create_video(image_path=image_path, duration=ttml_words[j]['end'] - duration)
        videos.append(VideoFileClip(video_url))
        duration = ttml_words[j]['end']
        


    # duration = 0
    # j = 0
    # videos = []

    # for video, line in zip(videos_path, ttml_two_lines):
    #     j += len(line['text'].split(' '))
    #     videos.append(adjust_video_duration(video, ttml_words[j]['end'] - duration + 1))
    #     duration = ttml_words[j]['end']
        
    create_slideshow(videos, ttml_words, ttml_lines, font=font_path, font_color=color, output_path = output_video_avi, addSubtitles=subtitles, font_size=80)

    if check_file_exists(ttml_file_lines) and check_file_exists(audio_path):
        add_audio_to_video(output_video_avi, audio_path, output_video_mp4)


    if output_video_mp4:
        return jsonify({'video_url': output_video_mp4})
    else:
        return jsonify({'error': 'Video generation failed.'}), 500

        
@app.route('/generate_image', methods=['POST'])
def generate_image():
    text = request.form.get('text')
    style_prompt = request.form.get('style_prompt')
    mood_prompt = request.form.get('mood_prompt')
    palette_prompt = request.form.get('palette_prompt')
    verse_index = int(request.form.get('verse_index'))
    image_index = int(request.form.get('image_index'))
    song_context = request.form.get('song_context') 

    mp3_file = request.files.get('mp3_file') 
    ttml_file = request.files.get('ttml_file') 
    lyrics_file = request.files.get('lyrics_file')
    
    # Translating lyrics and song context 
    seed = random.randint(0, 2**32 - 1)
    text_lines = text.split('\r\n')
    pair = ' '.join(text_lines)
    pair = song_context + ', ' + pair
    prompts = generate_prompt(pair)
    if len(prompts) == 0:
        prompts.append(translate_text(pair))
        prompts.append('')

    # Creating full prompt 
    full_prompt = prompts[0] + ' ' + style_prompt + ' ' + mood_prompt + ' ' + palette_prompt
    video_prompt = prompts[1]

    print(full_prompt)

    
    max_attempts = 5 
    attempts = 0
    image = None

    # Generating image max_attempts times
    while attempts < max_attempts:
        attempts += 1
        try: 
            model_response = query_model({
                "prompt": full_prompt,
                "seed": seed,
                "height": 480,
                "width": 848
            })

            if model_response["success"]:
                static_folder = os.path.join(os.getcwd(), "static")
                prompt_filename = os.path.join(static_folder, f"generate_image_{seed}_prompt.txt")
                with open(prompt_filename, 'w') as f:
                    f.write(video_prompt)
                    print(video_prompt)
                
                # Save mp3_file, ttml_file, lyrics_file on 00 image 
                if verse_index == 0 and image_index == 0:
                    if mp3_file:
                        mp3_filename = f'mp3_file.mp3'
                        mp3_path = os.path.join("static", mp3_filename)
                        mp3_file.save(mp3_path)
                    if ttml_file:
                        ttml_filename = f'ttml_file_lines.ttml'
                        ttml_path = os.path.join("static", ttml_filename)
                        ttml_file.save(ttml_path)
                    if lyrics_file:
                        lyrics_path = os.path.join("static", lyrics_file.filename)
                        lyrics_file.save(lyrics_path)
   
                return jsonify({
                    "image_url": model_response["image_url"],
                    "prompt": full_prompt
                })
            
            break  # If image open with success then leave from cycle

        except Exception as e:
            print(f"Ошибка при генерации изображения: {e}")
            time.sleep(60)

    if image is None:
        return jsonify({'error': 'Не удалось сгенерировать изображение после нескольких попыток.'}), 500



# Function for getting path to font
def get_font_path(font: str) -> str:
    font_paths = {
        "Faberge-Regular": "font/Faberge-Regular.otf",
        "BoldExtended": "font/BoldExtended.otf",
        "Plup": "font/Plup.ttf"
    }
    return font_paths.get(font, "font/Faberge-Regular.otf")

# Function for getting font color
def get_font_color(color:str) -> tuple[int, int, int, int]:
    font_colors = {
        "white": (255, 255, 255, 255),
        "red": (255, 0, 0, 255),
        "blue": (0, 0, 255, 255)
    }
    return font_colors.get(color,(255, 255, 255, 255))




if __name__ == '__main__':
     app.run(host="0.0.0.0", port=8000, debug=True)
