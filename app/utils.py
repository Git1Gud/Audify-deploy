from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip

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
