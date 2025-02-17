from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
from langchain_core.prompts import ChatPromptTemplate
from pydub.silence import split_on_silence
from langchain_ollama import OllamaLLM
from Backend.tiktokvoice import *
from datetime import timedelta
from pydub import AudioSegment
from termcolor import colored
from upload_youtube import *
import random
import time
import os

BACKGROUND_VIDEO_OPTIONS = os.listdir('clips')

CHAT_HISTORY_FILE = "chat_history.txt"

def load_chat_history(file_path):
    chat_history = []
    
    with open(file_path, "r") as file:
        content = file.read()

    sections = content.split("User:")

    for section in sections:
        if len(section) > 0:
            chat_history.append(f"User: {section}")

    return chat_history


def save_chat_history(file_path, history):
    """Save chat history to the file."""
    with open(file_path, "w") as file:
        for script in history:
            file.write(f"{script}\n")


# Function to convert timestamp tuple to seconds
def convert_tuple_to_seconds(time_tuple):
    h, m, s, ms = time_tuple

    ms = int(str(ms)[:3])

    return (h * 3600) + (m * 60) + s + (ms / 1000.0)

# Function to fix subtitle timestamp format
def fix_srt_timestamp_format(subtitles_filename):
    with open(subtitles_filename, 'r') as file:
        lines = file.readlines()

    # Iterate through each line and fix any timestamp issues
    for i, line in enumerate(lines):
        if '-->' in line:
            # Replace missing commas or dots
            if '.' not in line and ',' not in line:
                lines[i] = line.replace(' --> ', ',')

    # Save the fixed file
    with open(subtitles_filename, 'w') as file:
        file.writelines(lines)

# Function to parse SRT file and return subtitle data
def parse_srt(subtitles_filename):
    subtitles = []
    with open(subtitles_filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for i in range(0, len(lines), 4):
        time_range = lines[i + 1].strip()
        start_time, end_time = time_range.split(" --> ")

        # Convert times to tuple (h, m, s, ms)
        start_time = convert_srt_time_to_tuple(start_time)
        end_time = convert_srt_time_to_tuple(end_time)

        text = lines[i + 2].strip()

        subtitles.append(((start_time, end_time), text))

    return subtitles

# Convert SRT time format to tuple
def convert_srt_time_to_tuple(s):
    try:            
        if ',' in s:
            s, ms = s.split(',')
        elif '.' in s:
            s, ms = s.split('.')
        else:
            ms = 0

        h, m, s = map(int, s.split(":"))
        ms = int(ms)
        return (h, m, s, ms)
    except ValueError as e:
        print(f"Error converting time: {s}")
        raise e

def get_counter(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            content = file.read().strip()

        if not content:
            counter = 1
        else:
            counter = int(content)
        
    else:
        counter = 1

    with open(filepath, 'w') as file:
        file.write(str(counter))

    return counter

def save_counter(counter, filepath):

    with open(filepath, 'w') as file:
        file.write(str(counter))
    

# Function to add voice and subtitles to the video
def add_voice_and_subtitles_to_video(video_filename, voice_filename, subtitles_filename, output_filename):
    # Load video and voice
    video = VideoFileClip(video_filename)
    voice = AudioFileClip(voice_filename)

    # Get durations
    video_duration = video.duration
    voice_duration = voice.duration
    
    # Adjust video length to match voice length
    if voice_duration < video_duration:
        video = video.subclip(0, voice_duration)  # Trim video

    elif voice_duration > video_duration:
        loop_count = int(voice_duration // video_duration) + 1
        video = concatenate_videoclips([video] * loop_count).subclip(0, voice_duration)  # Loop video
    
    # Add voice to video
    video = video.set_audio(voice)

    # Load and parse subtitles
    subtitles = parse_srt(subtitles_filename)

    # Convert subtitle times to seconds
    subtitles = [((convert_tuple_to_seconds(start), convert_tuple_to_seconds(end)), text) for ((start, end), text) in subtitles]

    # Subtitle generator function (yellow font)
    def subtitle_generator(txt):
        return TextClip(txt, fontsize=95, color='yellow', font="fonts/bold_font.ttf", stroke_width=2)

    # Create SubtitlesClip from parsed subtitles
    subtitles_clip = SubtitlesClip(subtitles, subtitle_generator)

    # Combine video with subtitles
    video_with_subtitles = CompositeVideoClip([video, subtitles_clip.set_position(('center', 'center'))])

    # Write output file
    video_with_subtitles.write_videofile(output_filename, codec='libx264', audio_codec='aac')

# Function to generate SRT from chunks
def generate_srt(chunks, output_file="subtitles.srt"):
    with open(output_file, 'w', encoding='utf-8') as srt_file:
        for i, (start, end, text) in enumerate(chunks, start=1):
            # Convert start and end times to timedelta strings
            start_time = str(timedelta(milliseconds=start))
            end_time = str(timedelta(milliseconds=end))

            # Write subtitle entry to the file
            srt_file.write(f"{i}\n")
            srt_file.write(f"{start_time.replace('.', ',')} --> {end_time.replace('.', ',')}\n")
            srt_file.write(f"{text}\n\n")
    return output_file

# Function to process audio and generate subtitles
def process_audio_to_srt(audio_file, script, output_audio_dir="audio_chunks", srt_file="subtitles.srt", timestamp=""):
    if not os.path.exists(output_audio_dir):
        os.makedirs(output_audio_dir)

    # Load the audio file
    audio = AudioSegment.from_file(audio_file)

    # Try splitting audio by silence
    chunks = split_on_silence(
        audio,
        min_silence_len=300,  # Minimum silence length (in ms)
        silence_thresh=-35    # Silence threshold in dBFS
    )

    if len(chunks) < len(script):
        print("Insufficient chunks detected, falling back to fixed-duration splitting.")
        chunk_duration = len(audio) // len(script)  # Divide equally by script length
        chunks = [audio[i:i+chunk_duration] for i in range(0, len(audio), chunk_duration)]

    print(f"Number of chunks: {len(chunks)}")
    print(f"Number of script lines: {len(script)}")

    # Adjust script to match chunk count
    if len(script) < len(chunks):
        script.extend(["..."] * (len(chunks) - len(script)))  # Fill missing script lines with "..."
    elif len(chunks) < len(script):
        script = script[:len(chunks)]  # Truncate script

    subtitle_chunks = []
    current_time = 0

    for i, (chunk, text) in enumerate(zip(chunks, script)):
        start_time = current_time
        end_time = current_time + len(chunk)

        # Save chunk (optional)
        chunk.export(os.path.join(output_audio_dir, f"chunk_{i}.mp3"), format="mp3")

        # Add to subtitle list
        subtitle_chunks.append((start_time, end_time, text))

        current_time = end_time

    output_filename = f"{timestamp}.srt"
    return generate_srt(subtitle_chunks, output_file=output_filename)

try:

    filepath = 'counter.txt'

    counter = get_counter(filepath)

    youtube = authenticate_youtube()

    template = """
    I want to create a youtube shorts video. I want you to write a script. I have a program that takes a script in text and converts that text to audio, than add subtitles and add a background video and outputs a youtube shorts video. Now give me a scary story that would take around 60-95 seconds long to read. Don't write a harmful or violent script. I wan't the story to be unique, a story you haven't told anyone before, and it must be very scary. Use a simple english, no fancy advanced words. Don't give me anything except the story, so i don't want any title, or scenary of any type of explaination. Your answer should only be consisting of the story, and not anything else. Don't say 'The end' and don't use '...', use a simple english. Don't even add a sentece saying 'Here is your story' or i am telling the story or i will give you a story, you should only return me a story and nothing else

    Here is the conversation history:{context}

    Question: {question}

    Answer:
    """

    chat_history = load_chat_history(CHAT_HISTORY_FILE)
    # print("---------")
    # for history in chat_history:
    #     print(history)
    #     print("---------")

    model = OllamaLLM(model='llama3')
    prompt = ChatPromptTemplate.from_template(template)

    chain = prompt | model

    context = ""

    question = "Generate another different story for me"

    while True:
        start_time = time.time()
        timestamp = int(time.time())
        print("\n---------------------------------------\n")
        print(f"Generating new video, number {counter}")
        # print(f"Context > {context}")
        # print()

        script = chain.invoke({"context":context, "question":question})
        if len(script.split()) > 255:
            print("[Script too long, skipping]")
            question = "This script is too long, try to keep it under 255 words, generate another script for me"
            continue
        # print(f"Story > {script}")
        
        question = "Generate another different story for me"
        
        chat_history.append(f"\nUser: {question}\nAI: {script}")
        
        if len(chat_history) > 6:
            chat_history.pop(0)

        context = "".join(chat_history)


        save_chat_history(CHAT_HISTORY_FILE, chat_history)
        

        # if input("Choose voice or use default (ghostface) (y/n) > ") == "y":
        #     print("Voice choices")
        #     print("-------------")
        #     for i in range(len(VOICES)):
        #         print(f"{i+1} : {VOICES[i]}")

        #     voice_id = int(input("Enter voice number > "))
        #     voice = VOICES[voice_id - 1]

        # else:
        #     voice = VOICES[0]
        
        background_video = random.choice(BACKGROUND_VIDEO_OPTIONS)
        print(f"Selected {background_video} for background video")

        voice = VOICES[0]

        sound_filename = tts(text=script, voice=voice, timestamp=timestamp)

        print(f"Sound filename is: {sound_filename}")

        # Split script into chunks
        script = script.split()
        script_list = []

        line = ""
        for word in script:
            if len(line) > 8 and len(word) > 2:
                script_list.append(line.strip())
                line = ""
            line = f"{line} {word}".strip()

        if line:
            script_list.append(line)

        # print(f"Generated script list: {script_list}")

        # Process the audio and generate the subtitles
        subtitles_filename = process_audio_to_srt(sound_filename, script_list, timestamp=timestamp)

        print(f"Subtitles are saved to {subtitles_filename}")

        output_filename=f"outputs/{timestamp}.mp4"

        # Fix subtitle timestamp format before parsing
        fix_srt_timestamp_format(subtitles_filename)

        # Add voice and subtitles to the video

        add_voice_and_subtitles_to_video(video_filename=f"clips/{background_video}", voice_filename=sound_filename, subtitles_filename=subtitles_filename, output_filename=output_filename)

        print(f"Output number:{counter} is saved to {output_filename}")

        # video_response = upload_video(
        #                 video_path=os.path.abspath(output_filename),
        #                 title=f'Horror Stories - {counter}',
        #                 description='Short horror story',
        #                 category="28",
        #                 keywords='Horror story',
        #                 privacy_status='public'
        #             )

        
        video_name = f"Horror Stories - {counter}"
        video_id = upload_video(youtube,
                     video_name,
                     "28",
                     "Short horror story",
                     ["horror story", "short story"],
                     output_filename,
                     "public")
        
        print(colored(f"[UPLOADED] {video_name} is uploaded to youtube", "green"))
        print(colored(f"Video URL -> https://www.youtube.com/shorts/{video_id}", "blue"))
        

        os.remove(subtitles_filename)
        os.remove(sound_filename)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Video created and uploaded in {colored(int(elapsed_time), "green")} seconds")

        counter += 1

        save_counter(counter, filepath)
        
except:
    # Delete any unfinished videos or sounds and subtitles
    if subtitles_filename and os.path.isfile(subtitles_filename):
        os.remove(subtitles_filename)
    if sound_filename and os.path.isfile(sound_filename):
        os.remove(sound_filename)
    print("Exiting program")
    exit(0)