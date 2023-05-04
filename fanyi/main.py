import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageTk
import requests
import pytesseract
from pytesseract import Output
import json
import os
import keyboard
from tkinter import Toplevel
import pyautogui
from PIL import ImageDraw, ImageFont
import tempfile


def save_inputs(api_key, target_language):
    with open("inputs.json", "w") as f:
        json.dump({"api_key": api_key, "target_language": target_language}, f)


def load_inputs():
    if os.path.exists("inputs.json"):
        with open("inputs.json", "r") as f:
            return json.load(f)
    return {"api_key": "", "target_language": ""}


# GPT-3.5 API 调用
def translate_text(api_key, text, target_language):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "model": "gpt-3.5-turbo",  # 添加此行以指定模型
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Translate the following text to {target_language}: {text}"}
        ],
        "max_tokens": 100,
        "n": 1,
        "stop": None,
        "temperature": 0.8,
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def image_to_text(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text


def add_translated_text_to_image(image, translated_text):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 20)
    text_width = draw.textlength(translated_text, font=font)
    text_height = font.getmetrics()[0]
    draw.text(((image.width - text_width) / 2, (image.height - text_height) / 2), translated_text, font=font,
              fill="black")
    return image


# 截屏并翻译
def screenshot_and_translate(api_key, target_language):
    # 截取屏幕
    screen = pyautogui.screenshot()
    # 将截图保存为临时文件
    screen.save("screenshot.png")
    # 从截图中识别文本
    text = image_to_text("screenshot.png")
    # 使用 GPT-3 翻译文本
    translated_text = translate_text(api_key, text, target_language)
    # 在原始截图上添加翻译后的文本
    translated_image = add_translated_text_to_image(screen, translated_text)
    return translated_image, screen


# UI 设计
def on_start_button_click():
    api_key = api_key_entry.get()
    target_language = target_language_entry.get()
    save_inputs(api_key, target_language)

    floating_window = Toplevel(root)
    floating_window.overrideredirect(True)
    floating_window.attributes('-topmost', True)

    start_translation_button = tk.Button(floating_window, text="翻译", command=open_selection_window)
    start_translation_button.pack()

    def move_begin(event):
        floating_window.x = event.x
        floating_window.y = event.y

    def move_end(event):
        x = floating_window.winfo_pointerx() - floating_window.x
        y = floating_window.winfo_pointery() - floating_window.y
        floating_window.geometry(f"+{x}+{y}")

    floating_window.bind("<Button-1>", move_begin)
    floating_window.bind("<B1-Motion>", move_end)


def show_translated_image(api_key, target_language):
    translated_image, original_image = screenshot_and_translate(api_key, target_language)
    photo_translated = ImageTk.PhotoImage(translated_image)
    photo_original = ImageTk.PhotoImage(original_image)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    image_window = Toplevel(root)
    image_window.overrideredirect(True)
    image_window.geometry(f"{screen_width}x{screen_height}+0+0")
    image_window.attributes('-topmost', True)
    translated_image_label = tk.Label(image_window, image=photo_translated)
    translated_image_label.image = photo_translated
    translated_image_label.pack(fill="both", expand="yes")

    def toggle_image(event):
        nonlocal translated_image_label
        if translated_image_label.cget('image') == photo_translated:
            translated_image_label.config(image=photo_original)
            translated_image_label.image = photo_original
        else:
            translated_image_label.config(image=photo_translated)
            translated_image_label.image = photo_translated

    image_window.bind('<Button-1>', toggle_image)
    keyboard.add_hotkey('esc', image_window.destroy)


def open_selection_window():
    selection_window = tk.Toplevel(root)
    selection_window.attributes('-fullscreen', True)
    selection_window.attributes('-topmost', True)

    canvas = tk.Canvas(selection_window, bg='gray75', highlightthickness=0)
    canvas.pack(fill='both', expand=True)

    def start_selection(event):
        canvas.delete('selection_rectangle')
        canvas.start_x = event.x
        canvas.start_y = event.y

    def update_selection(event):
        canvas.delete('selection_rectangle')
        canvas.create_rectangle(canvas.start_x, canvas.start_y, event.x, event.y, outline='red', width=2,
                                tags='selection_rectangle')

    def finish_selection(event):
        x1 = min(canvas.start_x, event.x)
        y1 = min(canvas.start_y, event.y)
        x2 = max(canvas.start_x, event.x)
        y2 = max(canvas.start_y, event.y)
        selection_window.destroy()

        capture_and_translate(x1, y1, x2, y2)

    canvas.bind('<Button-1>', start_selection)
    canvas.bind('<B1-Motion>', update_selection)
    canvas.bind('<ButtonRelease-1>', finish_selection)


def capture_and_translate(x1, y1, x2, y2):
    api_key = api_key_entry.get()
    target_language = target_language_entry.get()

    # Capture selected area
    screen = ImageGrab.grab(bbox=(x1, y1, x2, y2))

    screen = screen.convert('RGB')  # Add this line to convert the image to RGB mode
    temp_fd, temp_file_name = tempfile.mkstemp(suffix=".jpg")
    os.close(temp_fd)
    screen.save(temp_file_name, format='JPEG')
    text = pytesseract.image_to_string(temp_file_name)
    os.unlink(temp_file_name)

    # Translate the extracted text
    translated_text = translate_text(api_key, text, target_language)

    # Add translated text to the image
    translated_image = add_translated_text_to_image(screen, translated_text)

    # Show the translated image
    show_translated_image(translated_image, target_language)


inputs = load_inputs()

root = tk.Tk()
root.title("实景翻译器")

api_key_label = tk.Label(root, text="API 密钥:")
api_key_label.grid(row=0, column=0)
api_key_entry = tk.Entry(root)
api_key_entry.insert(0, inputs["api_key"])
api_key_entry.grid(row=0, column=1)

target_language_label = tk.Label(root, text="目标语言:")
target_language_label.grid(row=1, column=0)
target_language_entry = tk.Entry(root)
target_language_entry.insert(0, inputs["target_language"])
target_language_entry.grid(row=1, column=1)

start_button = tk.Button(root, text="开始", command=on_start_button_click)
start_button.grid(row=2, column=0, columnspan=2)

root.mainloop()
