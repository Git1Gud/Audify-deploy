from flask import Blueprint, request, jsonify, send_file
from .utils import (
    convert_to_wav,
    censor_audio_from_video,
    censor_audio,
)
import os


base_audio_path = r"Media\extracted_audio.wav"
censor_audio_path = r"Media\overlay_audio.wav"
output_audio_path = r"Media\output_audio.wav"
output_video_path = r"Media\output_video_with_censored_audio.mp4"

model_name = 'small'
to_censor = ["kill", "killed", "fuck", "fucking", "killing"]

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
