import tensorflow as tf
import tensorflow_hub as hub
import csv
import librosa
import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
from moviepy.editor import VideoFileClip
import tempfile

class AudioPeakDetector:
    def __init__(self):
        # Load YAMNet model
        self.model = hub.load('https://tfhub.dev/google/yamnet/1')
        self.class_names = self._load_class_names()
        self.engagement_classes = ['Cheering', 'Applause', 'Crowd', 'Laughter']
        
    def _load_class_names(self):
        class_map_path = self.model.class_map_path().numpy()
        class_names = []
        with tf.io.gfile.GFile(class_map_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                class_names.append(row['display_name'])
        return class_names
    
    def extract_audio(self, video_path):
        """Extract audio from video file and save as temporary WAV"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmpfile:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(tmpfile.name, verbose=False, logger=None)
            video.close()
            return tmpfile.name
    
    def analyze_audio(self, audio_path):
        audio, sr = librosa.load(audio_path, sr=16000)
        
        scores, embeddings, spectrogram = self.model(audio)
        scores_np = scores.numpy()
        
        engagement_indices = [i for i, name in enumerate(self.class_names) 
                            if name in self.engagement_classes]
        engagement_scores = np.max(scores_np[:, engagement_indices], axis=1)
        
        # Temporal parameters
        time_per_frame = 0.48 
        times = np.arange(len(engagement_scores)) * time_per_frame
        
        return times, engagement_scores
    
    def detect_peaks(self, video_path, min_peak_height=0.06, min_distance=5):
        # Extract audio from video
        audio_path = self.extract_audio(video_path)
        
        # Analyze audio
        times, engagement = self.analyze_audio(audio_path)
        
        # Find peaks
        peaks, properties = find_peaks(engagement, 
                                     height=min_peak_height,
                                     distance=min_distance)
        
        return {
            'peak_times': times[peaks],
            'peak_scores': engagement[peaks],
            'engagement_curve': engagement,
            'timestamps': times
        }

def visualize_results(results):
    plt.figure(figsize=(15, 5))
    plt.plot(results['timestamps'], results['engagement_curve'], label='Engagement Level')
    plt.scatter(results['peak_times'], results['peak_scores'], 
               color='red', label='Detected Peaks')
    plt.title('Fan Engagement Peaks Detection')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Engagement Score')
    plt.legend()
    plt.grid(True)
    plt.show()

# Usage Example
if __name__ == "__main__":
    detector = AudioPeakDetector()
    results = detector.detect_peaks(r"C:\Users\DELL\Downloads\ipl.mp4") 
    
    print("Detected Peak Moments:")
    for time, score in zip(results['peak_times'], results['peak_scores']):
        print(f"- {time:.1f}s (confidence: {score:.2f})")
    
    visualize_results(results)
