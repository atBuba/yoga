import requests
import os 
import xml.etree.ElementTree as ET
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *
import random
from subtitles import *
from typing import Union
import re

# token for yandex translate 
IAM_TOKEN = 'AQVNzmvjqc5VLwWjpRWA_8XDFHOe0ybnBn4fhIAi'
folder_id = 'b1gbfto7jeu1ghuc8heq'
target_language = 'en'

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def translate_text(texts: str) -> str:
    '''
    Translates text from Russian to English (or another target language) 
    using the Yandex Translate API.

    Parameters:
    -----------
    texts : str
        The source text to be translated.

    Returns:
    --------
    str
        The translated text in the target language.
    '''

    body = {
        "targetLanguageCode": target_language,
        "texts": texts,
        "folderId": folder_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key {0}".format(IAM_TOKEN)
    }

    response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
        json=body,
        headers=headers
    )

    return response.json()['translations'][0]['text']



def generate_prompt(user_text):    
    # Собираем запрос
    data = {}
    # Указываем тип модели
    data["modelUri"] = f"gpt://{folder_id}/yandexgpt/rc"
    # Настраиваем опции
    data["completionOptions"] = {"temperature": 0.3, "maxTokens": 1000}
    # Указываем контекст для модели
    data["messages"] = [
        {"role": "system", "text": "напиши промт на английском языке для генерации изображения по двум строчкам из песни, затем напиши второй промт для анимации этого изображения изображения. Ответь в формате **Prompt 1** \nprompt \n**Prompt 2**\nprompt"},
        {"role": "user", "text": f"{user_text}"},
    ]
    
    # Отправляем запрос
    response = requests.post(
        URL,
        headers={
            "Accept": "application/json",
            "Authorization":  "Api-Key {0}".format(IAM_TOKEN)
        },
        json=data,
    ).json()

    #Распечатываем результат
    # message  = json.load(response)['result']['alternatives']['message']
    message = response['result']['alternatives'][0]['message']['text']
    prompts = re.findall(r'\*\*Prompt\s+\d+\*\*\s*:?[\s\n]*(.*?)(?=\n\*\*Prompt|\Z)', message, re.DOTALL)
    
    return prompts 



def add_audio_to_video(video_path: str, audio_path: str, output_path:str) -> None:
    '''
    Add audio to video and save in output_path

    Parameters:
    -----------
    video_path : str
        The path to avi video format to which the audio will be added
    audio_path: str
        The path to mp3 audio format to be added to the video    
    output_path: str
        The path where the mp4 file will be saved

    Returns:
    --------
    None
    '''

    video_clip = mp.VideoFileClip(video_path)
    audio_clip = mp.AudioFileClip(audio_path)
    
    # Trim audio and video to the same length
    if video_clip.duration <  audio_clip.duration:
        audio_clip = audio_clip.subclip(0, video_clip.duration)
    else:
        video_clip = video_clip.subclip(0, audio_clip.duration)

    video_with_audio = video_clip.set_audio(audio_clip)
    # Save mp4 video format in output_path 
    video_with_audio.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
def parse(ttml_file: str =None, txt_files: str =None, two_lines: bool = False,  word: bool = False) -> list[dict[str, Union[float, str]]]:
    '''
    Parses a TTML (Timed Text Markup Language) file or txt and extracts subtitles
    as a list of dictionaries with start time, end time, and text.

    Parameters:
    -----------
    ttml_file : str
        The path to the TTML file to be parsed.
    txt_file : str
        The path to the TTML file to be parsed.
    two_lines : bool
        True if you need to combine the text into two lines
    word : bool
        True if you need parse word in txt. file format 

    Returns:
    --------
    list[dict[str, str]]:
        A list of dictionaries, where each dictionary represents a subtitle entry
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle.
    '''

    slides = []

    #parse ttml
    if ttml_file:
        tree = ET.parse(ttml_file)
        root = tree.getroot()
        
        namespace = "{http://www.w3.org/ns/ttml}"  # Стандартное пространство имен TTML
        
        # Parsing ttml file and create list 
        for elem in root.findall(f".//{namespace}body//{namespace}p"):
            start_time = elem.attrib['begin']
            end_time = elem.attrib.get('end', None)
            text = elem.text.strip() if elem.text else ""
            
            slides.append({
                'start': start_time,
                'end': end_time,
                'text': text
            })
        
        # normalizing the ttml file (end word == start next word)
        for i in range(0, len(slides) - 1):
            slides[i]['end('] = slides[i + 1]['start']

        for i, line in enumerate(slides):
            line['start'] = float(line['start'][:-1:])
            line['end'] = float(line['end'][:-1:])

    #parse txt for lines 
    elif txt_files and not(word):
        duration_line = 4
        current_line = 0

        file = open(txt_files, 'r', encoding='utf-8') 
        lyrics = file.read().split('\n')[:-1:]

        for line in lyrics:
            slides.append({
                'start' : current_line,
                'end' : current_line + duration_line,
                'text' : line,
            })
            current_line += duration_line   

    #parse txt for words 
    elif txt_files and word:
        slides.append({
            'start' : 0,
            'end' : 0,
            'text' : '',
        })

        duration_line = 4
        duration_word = 0
        current_word = 0

        file = open(txt_files, 'r', encoding='utf-8') 
        lyrics = file.read().split('\n')

        for line in lyrics:
            duration_word = duration_line / len(line.split(' '))
            for word in line.split():
                slides.append({
                    'start' : current_word,
                    'end' : current_word + duration_word,
                    'text' : word,
                })
                current_word += duration_word   

    
    # combining lines
    if two_lines:
        slides_two_lines = []
        combinedText = ''
        combinedTextStart = 0
        combinedTextEnd = 0
        start = 0 
        end = 0
        
        for i in range(0, len(slides), 2):
            if i + 1 < len(slides):
                s = slides[i]['text'] +  ' \n' + slides[i + 1]['text']
                start = slides[i]['start']
                end = slides[i + 1]['end']
            else:
                s = slides[i]['text']
                start = slides[i]['start']
                end = slides[i]['end']

            


            if combinedText:
                s = combinedText + ' \n' + s
                combinedText = ''
                start = combinedTextStart
                combinedTextStart = 0
                combinedTextEnd = 0
            

            if len(s.split(' ')) <= 6:
                combinedText = s
                combinedTextStart = start 
                combinedTextEnd = end
            else:     
                slides_two_lines.append({
                'start': start,
                'end': end,
                'text':s
        })
            
        if (combinedTextStart == 0) and (combinedTextEnd ==  0):
            slides_two_lines.append({
                'start': combinedTextStart,
                'end': combinedTextEnd,
                'text':combinedText
            })

        slides = slides_two_lines[:-1:]

    return slides


def  create_subtitles(ttml_lines: list[dict[str, Union[float, str]]], ttml_words: list[dict[str, Union[float, str]]], font: str ="arial.ttf", font_color: str = 'white', size=(848, 480), font_size: int =40) -> list[CompositeVideoClip]:
    '''
    Create list of CompositeVideoClip of animated subtitles with a transparent background

    Parameters:
    -----------
    ttml_lines : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a line from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle.
    ttml_words : list[dict[str, Union[float, str]tr]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    font : str
        The path for .otf or .ttf file format
    font_color : str
        The color of the text

    Returns:
    --------
    list of CompositeVideoClip of subtitles with a transparent background
    '''

    final_video = []
    animations = [
        movie_latters,
        animate_words_pop_up,
        animate_cross,
        animate_words,
        animate_left_angle,
    ]

    word_number = 1
    animation_number = 0

    for i, line in enumerate(ttml_lines):
        animation  = animations[animation_number]
        words = ttml_words[word_number:word_number + len(line['text'].split())]

        animation_number += 1
        animation_number %= len(animations) 
        word_number += len(line['text'].split())
        clip = animation(text=line['text'], ttml=words, duration=words[-1]['end'] - words[0]['start'], font=font, font_color=font_color, size=size, font_size=font_size)
        final_video.append(clip.set_start(words[0]['start']))

    return final_video

def animation(image: ImageClip, animation: str) -> ImageClip:
    '''
    Сreates an animation of the appearance of an image

    Parameters:
    -----------
    image : ImageClip
        The image whose appearance should be animated
    animation : str
        The name of animation (fading, center, right2left, left2right)

    Returns:
    --------
    ImageClip with appearance animated  
    '''

    effect_duration = 0.1
    image_width = image.w
    step = image_width / effect_duration

    if animation == 'fading': 
        image = image.fadein(effect_duration)
    elif animation == 'center':
        image = image.set_position(('center', 'center'))
        image = image.resize(lambda t: 0.1 + 0.9 * min(t / effect_duration, 1))
    elif animation == 'rigth2left':
        image = image.set_position(
            lambda t: (image_width - step * t, 'center') if t < effect_duration else ('center', 'center')
        )
    elif animation == 'left2right':
        image = image.set_position(
            lambda t: (-image_width + step * t, 'center') if t < effect_duration else ('center', 'center')
        )
    
    return image

def create_slideshow(images: list[ImageClip] , ttml_words: list[dict] =None, ttml_lines: list[dict] =None, font: str ="arial.ttf", font_color: str='white', output_path:str ="combined_images.mp4", addSubtitles: bool =False, font_size: int =40) -> None:
    '''
    creates and saves videos in output_path with animated appearance of images and animated appearance of text

    Parameters:
    -----------
    images : list[ImageClip]
        The list of image whose be in video
    animation : str
        The name of animation (fading, center, right2left, left2right)
    ttml_lines : list[dict[str, str]]:
        A list of dictionaries, where each dictionary represents a line from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle.
    ttml_words : list[dict[str, str]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    font : str
        The path for .otf or .ttf file format
    font_color : str
        The color of the text
    addSubtitles : bool
        True if need add subtitles for video
    output_path : str
        The path where the video be saved 

    Returns:
    --------
    None
    '''
    animations = ['fading', 'rigth2left', 'left2right']
    animation_clips = []
    current_start_time = 0 
    video_size = images[0].size
    
    for image in images:
        anim = random.choice(animations)
        clip = animation(image, anim)
        clip = clip.set_start(current_start_time)
        current_start_time += clip.duration
        animation_clips.append(clip)
    
    # Concatenate animation clips
    final_clip = concatenate_videoclips(animation_clips, method="chain")
    
    # Create text clips
    if addSubtitles:
        text_clips = create_subtitles(ttml_lines, ttml_words, font=font, font_color=font_color, size=video_size, font_size=font_size)
        final_clip = CompositeVideoClip([final_clip] + text_clips)
    
    # Ensure output directory exists
    if not os.path.exists('video'):
        os.makedirs('video')
    
    # Write the final video file
    output_path = 'video/final_video.mp4'
    final_clip.write_videofile(output_path, fps=24, codec='libx264')
    print(f"Видео сохранено как: {output_path}")



def check_file_exists(file_path: str) -> bool:
    '''
    Cheak exists file in file_path

    Parameters:
    -----------
    file_path : str
        The path to the file 

    Returns:
    --------
    True - file in file path   
    False - else
    
    '''

    return os.path.exists(file_path)


def adjust_video_duration(video_path, required_duration):
    clip = VideoFileClip(video_path)
    current_duration = clip.duration
    if current_duration < required_duration:
        # Calculate how many times to repeat the video
        repeat_count = math.ceil(required_duration / current_duration)
        clips = [clip] * repeat_count
        extended_clip = concatenate_videoclips(clips)
        # Trim to required duration
        extended_clip = extended_clip.subclip(0, required_duration)
    else:
        # Trim to required duration
        extended_clip = clip.subclip(0, required_duration)
    return extended_clip
