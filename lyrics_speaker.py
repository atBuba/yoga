from manim import *
import random
import numpy as np
import sys
import librosa
import matplotlib.cm as cm

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
        current_y -= (line_obj.height / 2 + 0.1)  # Переход к следующей строке
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

        square_color = "#000000"
        square = Square(side_length=16, stroke_color=square_color, fill_color=square_color, fill_opacity=1).move_to([0, 14, 0])

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

        speed = 1
        distance = [0, 0, speed * (duration - appearance_duration - remove_duration)]

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
            text.animate(run_time=duration - appearance_duration - remove_duration).move_to(distance),
            square.animate(run_time=square_animation).scale(3.0).set_stroke(width=2).set_opacity(0),     
            rate_func=rate_functions.linear
        )

        self.remove(square)

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

    def create_equalizer(self, start_time, end_time, audio_path, appearance_duration=1.0, remove_duration=1.0):
        # Параметры
        N_BINS = 11  # Количество частотных бинов
        FPS = 30     # Частота кадров
        DURATION = end_time - start_time - appearance_duration - remove_duration  # Длительность в секундах
        MAX_HEIGHT = 5  # Максимальная высота столбца
        SEGMENT_HEIGHT = 0.15  # Высота одного маленького прямоугольника
        MAX_SEGMENTS = int(MAX_HEIGHT / SEGMENT_HEIGHT)  # Максимальное количество сегментов
        bar_width = 0.6
        bars_bottom = DOWN * 2.5
        bars_indent = 0.1 
        
        # Загрузка аудиофайла
        y, sr = librosa.load(audio_path, offset=start_time + appearance_duration, duration=DURATION)
        if len(y) == 0:
            print(f"Warning: Empty audio segment at {start_time}")
            return
        
        # Спектрограмма
        hop_length = int(sr / FPS)  # Длина шага для соответствия FPS
        S = librosa.stft(y, hop_length=hop_length)
        S_dB = librosa.amplitude_to_db(np.abs(S), ref=np.max)
        
        num_frames = S_dB.shape[1]  # Количество кадров
        freq_bins = S_dB.shape[0]   # Количество частотных бинов
        
        # Группировка в N_BINS
        bin_indices = np.linspace(0, freq_bins, N_BINS + 1, dtype=int)
        bin_powers = np.array([
            np.mean(S_dB[bin_indices[i]:bin_indices[i + 1], :], axis=0)
            for i in range(N_BINS)
        ])
        
        # Сохраняем bin_powers для update_bars
        global_bin_powers = bin_powers.copy()
        
        # Функция для создания симметричного распределения высот
        def apply_symmetric_weights(powers, n_bins=N_BINS):
            center = (n_bins - 1) / 2
            weights = np.array([1.0 - 0.8 * abs(i - center) / center for i in range(n_bins)])
            return powers * weights

        # Создание столбцов из маленьких прямоугольников
        bars = VGroup()
        bar_groups = []  # Для хранения групп прямоугольников каждого столбца
        base_positions = []  # Для хранения базовых позиций столбцов
        initial_segments = []  # Для хранения начального количества сегментов
        
        # Начальные высоты для первого кадра с нормализацией
        frame_powers = bin_powers[:, 0]
        min_power = np.min(frame_powers)
        max_power = np.max(frame_powers) if np.max(frame_powers) > min_power else min_power + 1.
        normalized_frame_powers = (frame_powers - min_power) / (max_power - min_power)
        symmetric_powers = apply_symmetric_weights(normalized_frame_powers)
        
        for i in range(N_BINS):
            bar_group = VGroup()
            base_x = (i - (N_BINS - 1) / 2) * (bar_width + bars_indent)  # Центрирование столбцов
            total_height = symmetric_powers[i] * MAX_HEIGHT
            num_segments = max(2, min(int(total_height / SEGMENT_HEIGHT), MAX_SEGMENTS))
            initial_segments.append(num_segments)
            
            for j in range(num_segments):
                segment = Rectangle(
                    width=bar_width,
                    height=SEGMENT_HEIGHT,
                    fill_opacity=1.0,
                )
                segment.set_fill(WHITE)
                y_pos = bars_bottom[1] + (j + 0.5) * (SEGMENT_HEIGHT + bars_indent)
                # Начальная позиция с z_offset, как в _move_1
                z_offset = 40 + random.uniform(-15, 15)
                segment.move_to([base_x, y_pos, z_offset])
                bar_group.add(segment)
            
            base_positions.append([base_x, -MAX_HEIGHT / 2, 0])
            bar_groups.append(bar_group)
            bars.add(bar_group)
        
        self.add(bars)

        # Анимация появления, как в _move_1
        animations = []
        for bar_group in bar_groups:
            for segment in bar_group:
                target_pos = segment.get_center() - OUT * segment.get_center()[2]  # z=0
                animations.append(
                    segment.animate.move_to(target_pos)
                )

        self.play(
            *animations,
            run_time=appearance_duration,
            rate_func=rate_functions.ease_out_expo
        )

        # Сброс времени рендера
        self.renderer.time = 0

        # Функция обновления высоты баров с динамической нормализацией
        def update_bars(obj, dt):
            frame_index = self.renderer.time * FPS
            floor_index = int(frame_index)
            frac = frame_index - floor_index

            if frame_index == 0:
                for bar_group in bar_groups:
                    bar_group.remove(*bar_group[2:].submobjects) 
                return
            
            if floor_index >= num_frames:
                return
            
            # Линейная интерполяция между кадрами
            frame_powers = (1 - frac) * global_bin_powers[:, floor_index] + \
                          frac * global_bin_powers[:, min(floor_index + 1, num_frames - 1)]
            
            # Динамическая нормализация для текущего кадра
            min_power = np.min(frame_powers)
            max_power = np.max(frame_powers) if np.max(frame_powers) > min_power else min_power + 1
            normalized_powers = (frame_powers - min_power) / (max_power - min_power)
            symmetric_powers = apply_symmetric_weights(normalized_powers)

            for i, (bar_group, height, base_pos) in enumerate(zip(bar_groups, symmetric_powers, base_positions)):
                # Очищаем старые прямоугольники
                bar_group.remove(*bar_group.submobjects)
                total_height = height * MAX_HEIGHT
                num_segments = max(2, min(int(total_height / SEGMENT_HEIGHT), MAX_SEGMENTS))
                
                # Создаём новые прямоугольники
                for j in range(num_segments):
                    segment = Rectangle(
                        width=bar_width,
                        height=SEGMENT_HEIGHT,
                        fill_opacity=1.0,
                    )
                    segment.set_fill(WHITE)
                    y_pos = bars_bottom[1] + (j + 0.5) * (SEGMENT_HEIGHT + bars_indent)
                    segment.move_to([base_pos[0], y_pos, 0])  # Остаёмся в z=0
                    bar_group.add(segment)

            

        # Привязка обновления
        bars.add_updater(update_bars)

        # Установка длительности сцены
        self.wait(DURATION)

        # Остановка обновления
        bars.clear_updaters()

        # Анимация исчезновения, как в _move_2
        animations_remove = []
        for bar_group in bar_groups:
            for segment in bar_group:
                z_offset = random.uniform(10, 40)  # За камеру
                remove_pos = segment.get_center() + OUT * z_offset
                animations_remove.append(
                    segment.animate.move_to(remove_pos).set_opacity(0)
                )

        self.play(
            *animations_remove,
            run_time=remove_duration,
            rate_func=smooth
        )

        # Полная очистка объектов
        for bar_group in bar_groups:
            bar_group.remove(*bar_group.submobjects)
            bars.remove(bar_group)
        bars.remove(*bars.submobjects)
        self.remove(bars)
        bar_groups.clear()
        bars.submobjects.clear()

    def construct(self):
        self.camera.background_opacity = 0.0
        self.camera.background_color = None
        self.set_camera_orientation(gamma=0 * DEGREES, phi=0 * DEGREES, theta=-90 * DEGREES)
    
        # Получаем путь к .srt и шрифт из аргументов командной строки
        srt_file_path = sys.argv[3]  # Первый аргумент после имени скрипта
        font = sys.argv[4]  
        audio_path = sys.argv[5] 
        print(audio_path)
        lyrics = parse_srt(srt_file_path)
    
        max_width = 6.0
        target_width = 6.0

        previous_effect = None
        
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
            if start_time - (current_time + 0.5) > 5.0:
                print(f"Creating equalizer from {current_time} to {start_time - 0.5}")
                self.create_equalizer(current_time, start_time - 0.5, audio_path)
                duration -= (start_time - current_time - 0.5)
            elif start_time > current_time + 0.5:
                pause_duration = start_time - current_time - 0.5
                print(f"Pausing for {pause_duration} seconds (start: {start_time}, current: {current_time})")
                duration -= pause_duration
                self.wait(pause_duration)
    
            if text:  
                # Применяем эффект к тексту
                effect = random.choice(EFFECTS)
                while effect == previous_effect:
                    effect = random.choice(EFFECTS)
                previous_effect = effect
                text = effect(self, text, duration=duration)
                self.remove(*text)
                current_time = end_time  # Обновляем текущее время после текста

if __name__ == "__main__":
    config["output_file"] = "output_video.mp4"
    scene = LyricsSpeakerBox()
    scene.render()