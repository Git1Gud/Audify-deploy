from flask import Blueprint, request, jsonify, send_file
import os
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import whisper

base_audio_path = r"Media\extracted_audio.wav"
censor_audio_path = r"Media\overlay_audio.wav"
output_audio_path = r"Media\output_audio.wav"
output_video_path = r"Media\output_video_with_censored_audio.mp4"

model_name = 'small'
to_censor = ["kill", "killed", "fuck", "fucking", "killing"]



def censor_audio(base_audio_path, censor_audio_path, output_audio_path, model_name, to_censor, gain_of_censor=0, gain_of_base=0, silent=True):
    print('Censoring started')
    time_list = timestamp_list(base_audio_path, model_name)

    def find_time_occurrences(to_censor):
        result = []
        for word in to_censor:
            word = word.lower()
            for item in time_list:
                if item[0] == word:
                    print(f'Censoring {item[0]} from {item[1]} to {item[2]} seconds')
                    result.append((item[1] * 1000, item[2] * 1000))  
        return result

    censor_times = find_time_occurrences(to_censor)

    base_audio = AudioSegment.from_file(base_audio_path)
    censor_audio = AudioSegment.from_file(censor_audio_path)

    if gain_of_censor is not None:
        censor_audio = censor_audio + gain_of_censor

    for start_time, end_time in censor_times:
        end_time+=250
        duration = end_time - start_time 
        censor_segment = censor_audio[:duration] 

        while len(censor_segment) < duration:
            censor_segment += censor_audio

        censor_segment = censor_segment[:duration]  

        if silent:
            silence = AudioSegment.silent(duration=duration)
            base_audio = base_audio[:start_time] + silence + base_audio[end_time:]
        else:
            base_audio = base_audio[:start_time] + censor_segment + base_audio[end_time:]

    base_audio.export(output_audio_path, format="wav")
    print(f"Censored audio saved to {output_audio_path}")
    return output_audio_path

    



def convert_to_wav(input_audio_path, output_audio_path):
    try:
        audio = AudioSegment.from_file(input_audio_path) 
        audio.export(output_audio_path, format="wav") 
    except Exception as e:
        raise ValueError(f"Error converting audio to WAV: {str(e)}")



def censor_audio_from_video(input_video_path, output_video_path, to_censor):
    # Extract audio from video
    video = VideoFileClip(input_video_path)
    audio = video.audio
    audio_path = "temp_audio.wav"
    audio.write_audiofile(audio_path)
    
    # Convert the extracted audio to .wav format
    convert_to_wav(audio_path, base_audio_path)
    os.remove(audio_path)
    
    # Perform the censorship on the audio
    censor_audio(
        base_audio_path=base_audio_path,
        censor_audio_path=censor_audio_path,
        output_audio_path=output_audio_path,
        model_name=model_name,
        to_censor=to_censor,
        gain_of_censor=0,
        gain_of_base=-100,
        silent=False
    )
    
    # Replace the original audio with the censored audio in the video
    censored_audio = AudioFileClip(output_audio_path)
    final_video = video.set_audio(censored_audio)
    final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

    # Clean up
    video.close()
    censored_audio.close()
import whisper
import torch
from pydub import AudioSegment

class Word:
    def __init__(self, data):
        self.conf = data["conf"]
        self.end = data["end"]
        self.start = data["start"]
        self.word = data["word"]

    def to_string(self):
        return f"{self.word:20} from {self.start:.2f} sec to {self.end:.2f} sec, confidence is {self.conf * 100:.2f}%"

    def start_point(self):
        return [self.word,self.start,self.end]
    

def timestamp_list(base_audio_path, model_name="base"):
    
    model = whisper.load_model(model_name,device="cuda" if torch.cuda.is_available() else "cpu")

    result = model.transcribe(base_audio_path, word_timestamps=True, language="en")
    print(result['text'],'\n')

    list_of_Words = []
    for segment in result['segments']:
        for word in segment['words']:
            x=word['word'].strip().lower()
            if x[len(x)-1]=='.' or x[len(x)-1]==',' or x[len(x)-1]=='?' or x[len(x)-1]=='!':
                x=x[:len(x)-1]
            w = Word({
                "conf": word['probability'], 
                "start": word["start"],
                "end": word["end"],
                "word": x
            })
            list_of_Words.append(w)

    final = []
    for word in list_of_Words:
        time = word.start_point()
        final.append(time)
    
    return final



bp = Blueprint('main', __name__)

@bp.route('/upload', methods=['POST'])
def upload_audio():
    if 'base' not in request.files:
        return jsonify({"error": "Missing 'base' audio file."}), 400

    base_audio = request.files['base']
    base_audio.save("temp_base_audio")  
    convert_to_wav("temp_base_audio", base_audio_path)  
    os.remove("temp_base_audio")

    overlay_audio = request.files.get('overlay')
    if overlay_audio and overlay_audio.filename:
        overlay_audio.save("temp_overlay_audio")  
        convert_to_wav("temp_overlay_audio", censor_audio_path)
        os.remove("temp_overlay_audio")

    censor_words = request.form.get('censor_words')
    if censor_words:
        try:
            global to_censor
            to_censor = censor_words.split(",") 
        except Exception as e:
            return jsonify({"error": f"Invalid censor words format: {str(e)}"}), 400
    
    return jsonify({"message": "Files and censor words uploaded successfully.", "censor_words": to_censor}), 200


@bp.route('/censor', methods=['GET'])
def censor_get():
    if not base_audio_path:
        return jsonify({"error": "Base audio file not found. Please upload first."}), 404

    censor_audio(
        base_audio_path=base_audio_path,
        censor_audio_path=censor_audio_path,
        output_audio_path=output_audio_path,
        model_name=model_name,
        to_censor=to_censor,  
        gain_of_censor=0,
        gain_of_base=-100,
        silent=False
    )
    print('Censoring done')
    return send_file(output_audio_path, mimetype='audio/wav')


@bp.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "Missing video file."}), 400

    video_file = request.files['video']
    video_path = "temp_video.mp4"
    video_file.save(video_path)

    censor_words = request.form.get('censor_words')
    if censor_words:
        try:
            global to_censor
            to_censor = censor_words.split(",") 
        except Exception as e:
            return jsonify({"error": f"Invalid censor words format: {str(e)}"}), 400
    print(to_censor)
    # Process the video to extract audio, censor it, and put it back
    try:
        censor_audio_from_video(video_path, output_video_path, to_censor)
        print('Censoring done')
    except Exception as e:
        return jsonify({"error": f"Error processing video: {str(e)}"}), 500
    finally:
        # Clean up the uploaded video file
        os.remove(video_path)

    return jsonify({"message": "Video uploaded and processed successfully."}), 200

@bp.route('/get_video', methods=['GET'])
def get_video():
    if not os.path.exists(output_video_path):
        return jsonify({"error": "No processed video available."}), 404

    return send_file(output_video_path, mimetype='video/mp4')


@bp.route('/')
def upload_page():
    censor_words_display = ", ".join(to_censor) if to_censor else "None"
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Upload Audio</title>
    </head>
    <body>
        <h1>Upload Audio File</h1>
        <p><strong>Current Censor Words:</strong> {censor_words_display}</p>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <label>Base Audio:</label>
            <input type="file" name="base" accept=".wav, .mp3, .ogg" required><br><br>
            <label>Overlay Audio (optional):</label>
            <input type="file" name="overlay" accept=".wav, .mp3, .ogg"><br><br>
            <label>Censor Words (comma-separated):</label>
            <input type="text" name="censor_words" placeholder="e.g., kill,killed,fuck"><br><br>
            <button type="submit">Upload</button>
        </form>
        <h2>Censor Audio</h2>
        <form action="/censor" method="GET">
            <button type="submit">Censor Uploaded Audio</button>
        </form>
    </body>
    </html>
    '''


@bp.route('/video')
def upload_video_page():
    censor_words_display = ", ".join(to_censor) if to_censor else "None"
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Upload Video</title>
    </head>
    <body>
        <h1>Upload Video File</h1>
        <p><strong>Current Censor Words:</strong> {censor_words_display}</p>
        <form action="/upload_video" method="POST" enctype="multipart/form-data">
            <label>Video:</label>
            <input type="file" name="video" accept=".mp4, .avi, .mov, .mkv" required><br><br>
            <label>Censor Words (comma-separated):</label>
            <input type="text" name="censor_words" placeholder="e.g., kill,killed,fuck"><br><br>
            <button type="submit">Upload Video</button>
        </form>
        <h2>Download Processed Video</h2>
        <form action="/get_video" method="GET">
            <button type="submit">Get Processed Video</button>
        </form>
    </body>
    </html>
    '''
