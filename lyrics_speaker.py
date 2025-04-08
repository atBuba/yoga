from manim import *
import random
import numpy as np
import sys

EFFECTS = [
    lambda s, line, duration: s._move_1(line, duration),
    lambda s, line, duration: s._move_2(line, duration),
    lambda s, line, duration: s._move_3(line, duration),
    lambda s, line, duration: s._move_4(line, duration),
    # lambda s, line, duration: s._move_5(line, duration),
]

def parse_srt(file_path):
    """
    Читает .srt файл и возвращает список словарей с временем начала, конца и текстом.
    """
    import re

    lyrics = []
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.read().strip().split('\n\n')

        for entry in lines:
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split('\n')
            if len(parts) < 2:
                continue

            time_line = parts[1]
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', time_line)
            if not match:
                continue

            start_time_str, end_time_str = match.groups()

            # Преобразуем время начала в секунды
            hours, minutes, seconds = map(int, start_time_str.replace(',', ':').split(':')[:3])
            milliseconds = int(start_time_str.split(',')[1])
            start_time = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

            # Преобразуем время конца в секунды
            hours, minutes, seconds = map(int, end_time_str.replace(',', ':').split(':')[:3])
            milliseconds = int(end_time_str.split(',')[1])
            end_time = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

            # Текст субтитров
            text = '\n'.join(parts[2:]).strip()

            lyrics.append({"start_time": start_time, "end_time": end_time, "text": text})

    return lyrics

def adjust_text_to_width(text, max_width, target_width, color=WHITE, weight="BOLD", stroke_width=2, stroke_color=BLACK, font=""):
    """
    Принимает текст, разбивает его на строки с учетом max_width,
    и увеличивает масштаб каждой строки, если она меньше target_width.
    Возвращает VGroup с отмасштабированными строками, отступы зависят от высоты строк.
    """
    text_obj = Text(text, weight=weight, color=color, font=font).scale(1.0)
    
    if text_obj.width > max_width:
        words = text.split()
        lines = []
        current_line = ""
        current_width = 0
        
        for word in words:
            word_obj = Text(word, weight=weight, color=color, font=font).scale(1.0)
            if current_width + word_obj.width + 0.2 > max_width:
                lines.append(current_line.rstrip())
                current_line = word + " "
                current_width = word_obj.width + 0.2
            else:
                current_line += word + " "
                current_width += word_obj.width + 0.2
        lines.append(current_line.rstrip())
    else:
        lines = [text]

    line_objects = []
    total_height = 0  # Суммарная высота для центрирования
    for i, line in enumerate(lines):
        line_obj = Text(line, weight=weight, color=color, font=font).scale(1.0)
        if line_obj.width < target_width and line_obj.width != 0:
            scale_factor = target_width / line_obj.width
            line_obj.scale(scale_factor)
        line_objects.append(line_obj)
        total_height += line_obj.height  # Суммируем высоту каждой строки

    # Вычисляем позиции строк с учетом их высоты
    current_y = total_height / 2  # Начинаем с верхней позиции
    for i, line_obj in enumerate(line_objects):
        # Смещаем строку вниз от текущей позиции на половину её высоты
        current_y -= line_obj.height / 2  # Центр текущей строки
        line_obj.shift(UP * current_y)
        current_y -= (line_obj.height / 2 + 0.1)# Переход к следующей строке с учетом её высоты

    text_group = VGroup(*line_objects)
    text_group.move_to(ORIGIN)
    return text_group

class LyricsSpeakerBox(ThreeDScene):
    def _move_1(self, text, duration, appearance_duration=1.0, remove_duration=0.5):
        
        if duration < appearance_duration + remove_duration:
            appearance_duration = 0.25 * duration
            remove_duration = 0.25 * duration

        text.move_to([0, 0, 21])
        chars_start = VGroup(*[char for line in text for char in line]) 

        # square_color = text.get_color()
        square_color = "#000000"
        square = Square(side_length=16, stroke_color=square_color, fill_color=square_color,fill_opacity=1).move_to([0, 14, 0])

        current_char = 0
        for _, line in enumerate(chars_start):
            for _, char in enumerate(line): 
                z_offset = random.uniform(-15, +15)  
                start_positions = char.get_center() + OUT * z_offset  
                char.move_to(start_positions)  
                current_char += 1

        animations = []
        for i, char in enumerate(chars_start):
            animations.append(
                char.animate.move_to(char.get_center() - OUT * char.get_center()[2])  
            )

        self.play(
            *animations,
            run_time=appearance_duration,
            rate_func=rate_functions.ease_out_expo
        )

        speed = -1
        distance = [0, 0, speed * (duration - appearance_duration - remove_duration)]

        # Ждем оставшееся время
        self.play(
            chars_start.animate.move_to(distance),
            run_time=duration - appearance_duration - remove_duration,
            rate_func=rate_functions.linear
        )

        animations_remove = []
        for i, char in enumerate(chars_start):
            z_offset = random.uniform(-30, -80)  
            remove_positions = char.get_center() + OUT * z_offset  
            animations_remove.append(
                char.animate.move_to(remove_positions).set_opacity(0)  
            )

        self.play(
            *animations_remove,
            run_time=remove_duration,
            rate_func=smooth
        )

        return chars_start 
    
    
    def _move_2(self, text, duration, appearance_duration=0.75, remove_duration=0.5):

        if duration < appearance_duration + remove_duration:
            appearance_duration = 0.25 * duration
            remove_duration = 0.25 * duration

        text.move_to([0, 0, -60])
        chars_start = VGroup(*[char for line in text for char in line]) 

        current_char = 0
        for _, line in enumerate(chars_start):
            for _, char in enumerate(line): 
                z_offset = random.uniform(-25, +25)  
                start_positions = char.get_center() + OUT * z_offset  
                char.move_to(start_positions)  
                current_char += 1

        animations = []
        for i, char in enumerate(chars_start):
            animations.append(
                char.animate.move_to(char.get_center() - OUT * char.get_center()[2])  
            )

        self.play(
            *animations,
            run_time=appearance_duration,
            rate_func=rate_functions.ease_out_expo
        )

        # Ждем оставшееся время
        speed = 1
        distance = [0, 0, speed * (duration - appearance_duration - remove_duration)]

        # Ждем оставшееся время
        self.play(
            chars_start.animate.move_to(distance),
            run_time=duration - appearance_duration - remove_duration,
            rate_func=rate_functions.linear
        )

        animations_remove = []
        for i, char in enumerate(chars_start):
            z_offset = random.uniform(10, 40)  
            remove_positions = char.get_center() + OUT * z_offset  
            animations_remove.append(
                char.animate.move_to(remove_positions).set_opacity(0)  
            )

        self.play(
            *animations_remove,
            run_time=remove_duration,
            rate_func=smooth
        )

        return chars_start 
    

    def _move_3(self, text, duration, appearance_duration=1, remove_duration=0.5, square_animation=0.4):
        text = text.rotate(PI/10)
        text.move_to([0, 0, 25])

        if duration < appearance_duration + remove_duration:
            appearance_duration = 0.25 * duration
            remove_duration = 0.25 * duration

            if duration - appearance_duration - remove_duration < square_animation:
                square_animation = duration
        
        square_color = text.get_color()

        # Создаем квадратную рамку на заднем плане
        square = Square(side_length=2, fill_opacity=0, stroke_width=20, stroke_color=square_color)
        square.move_to(ORIGIN).rotate(PI/4) 

    
        self.play(
            text.animate.move_to(ORIGIN),  
            run_time=appearance_duration,               
            rate_func=rate_functions.rush_from
        )
        
        speed = -2
        distance = [0, 0, speed * (duration - appearance_duration - remove_duration)]

        self.play(
            text.animate(run_time=duration - appearance_duration - remove_duration,).move_to(distance),
            square.animate(run_time=square_animation).scale(3.0).set_stroke(width=2).set_opacity(0),     
            rate_func=rate_functions.linear
        )

        self.remove(square)

        # self.wait(duration - appearance_duration - remove_duration - square_animation)

        self.play(
            ShrinkToCenter(text),
            run_time=remove_duration,
            rate_func=rate_functions.rush_into
        )

        return text

    def _move_4(self, text, duration, appearance_duration=1.0, remove_duration=0.75):

        if duration < appearance_duration + remove_duration:
            appearance_duration = 0.25 * duration
            remove_duration = 0.25 * duration

        
        about_point = [0, -8, 0]
        angle = PI / 2

        text.move_to(ORIGIN)

        self.play(
            AnimationGroup(*[FadeIn(char, shift=DOWN) for char in text], lag_ratio=0.5, run_time=appearance_duration),
        )

        # Ждем оставшееся время
        self.wait(duration - appearance_duration - remove_duration)

        self.play(
            Rotate(
                text, 
                angle=angle,
                about_point=about_point
                ),
            run_time=remove_duration,
            rate_func=rate_functions.ease_in_out_cubic,
        )
        return text 
    
    def _move_5(self, text, duration, appearance_duration=0.75, remove_duration=0.75):

        if duration < appearance_duration + remove_duration:
            appearance_duration = 0.25 * duration
            remove_duration = 0.25 * duration

        text = text.apply_function(lambda point: [point[0], point[1], 20 + point[0] ** 4 + point[1] ** 4]).rotate(PI/4)
        ugol = -PI/ 80
        self.play(
            text.animate.apply_function(lambda point: [point[0], point[1], 0]).rotate(-PI/4 - ugol),
            rate_func=rate_functions.rush_from,
            run_time=appearance_duration,
        )

        self.play(
            text.animate.rotate(ugol),
            rate_func=rate_functions.linear,
            run_time=duration - appearance_duration - remove_duration,
        )

        self.play(
            text.animate.apply_function(lambda point: [point[0], point[1], 20 + point[0] ** 4 + point[1] ** 4]).rotate(-PI/4),
            run_time=remove_duration,
        )
        
        return text 


    def construct(self):
        self.camera.background_opacity = 0.0
        # self.camera.background_color = "#5eb7cd"
        self.set_camera_orientation(gamma=0 * DEGREES, phi=0 * DEGREES, theta=-90 * DEGREES)
    
        # Получаем путь к .srt и шрифт из аргументов командной строки
        srt_file_path = sys.argv[3]  # Первый аргумент после имени скрипта
        font = sys.argv[4]  
        print(srt_file_path)
        lyrics = parse_srt(srt_file_path)
    
        max_width = 6
        target_width = 6
    
        text_objs = []
        for line in lyrics:
            line_text = line['text'].strip()
            if line_text == "-":
                text_objs.append(None)
            else:
                adjusted_text = adjust_text_to_width(line_text, max_width, target_width, color=WHITE, weight="LIGHT", font=font)
                text_objs.append(adjusted_text)
    
        current_time = 0.0
        for i in range(len(text_objs)):
            text = text_objs[i]
            start_time = lyrics[i]['start_time']
            end_time = lyrics[i]['end_time']
            duration = end_time - current_time
    
            # Обрабатываем паузу перед текущей строкой
            if start_time > current_time + 0.5:
                pause_duration = start_time - current_time - 0.5
                duration -= pause_duration
                self.wait(pause_duration)
    
            if text:  
                # Применяем эффект к тексту
                effect = random.choice(EFFECTS)
                text = effect(self, text, duration=duration)
                self.remove(*text)
                current_time = end_time  # Обновляем текущее время после текста


if __name__ == "__main__":
    config["output_file"] = "output_video.mp4"
    scene = LyricsSpeakerBox()
    scene.render()
