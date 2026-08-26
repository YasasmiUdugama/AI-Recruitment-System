import os
import logging
import tempfile
import numpy as np

logger = logging.getLogger('ai_recruitment')

try:
    import whisper
    WHISPER_AVAILABLE = True
    _whisper_model = None
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("OpenAI Whisper not available. Speech-to-text disabled.")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("Librosa not available. Voice feature analysis disabled.")


def get_whisper_model(model_name='base'):
    """Lazy load Whisper model"""
    global _whisper_model
    if _whisper_model is None and WHISPER_AVAILABLE:
        logger.info(f"Loading Whisper model: {model_name}")
        try:
            _whisper_model = whisper.load_model(model_name)
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
    return _whisper_model


def speech_to_text(audio_file_path, model_name='base'):
    if not WHISPER_AVAILABLE:
        logger.warning("Whisper not available for speech-to-text")
        return {
            'text': '[Speech-to-text unavailable - Whisper not installed]',
            'language': 'unknown',
            'confidence': 0
        }

    if not os.path.exists(audio_file_path):
        logger.error(f"Audio file not found: {audio_file_path}")
        return {
            'text': '[Audio file not found]',
            'language': 'unknown',
            'confidence': 0
        }

    try:
        model = get_whisper_model(model_name)
        if model is None:
            return {
                'text': '[Failed to load Whisper model]',
                'language': 'unknown',
                'confidence': 0
            }

        logger.info(f"Transcribing audio: {audio_file_path}")
        result = model.transcribe(audio_file_path)

        return {
            'text': result.get('text', ''),
            'language': result.get('language', 'unknown'),
            'confidence': result.get('confidence', 0),
            'segments': result.get('segments', [])
        }

    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        return {
            'text': f'[Transcription error: {str(e)}]',
            'language': 'unknown',
            'confidence': 0
        }


def analyze_voice_features(audio_file_path):

    if not LIBROSA_AVAILABLE:
        logger.warning("Librosa not available for voice analysis")
        return {
            'pitch': 0,
            'energy': 0,
            'tempo': 0,
            'zero_crossing_rate': 0,
            'spectral_centroid': 0,
            'confidence_score': 0,
            'error': 'Librosa not installed'
        }

    if not os.path.exists(audio_file_path):
        logger.error(f"Audio file not found: {audio_file_path}")
        return {
            'pitch': 0,
            'energy': 0,
            'tempo': 0,
            'zero_crossing_rate': 0,
            'spectral_centroid': 0,
            'confidence_score': 0,
            'error': 'File not found'
        }

    try:
        y, sr = librosa.load(audio_file_path, sr=None)

        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = pitches[pitches > 0]
        avg_pitch = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0

        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms))

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 0
        else:
            tempo = float(tempo)

        zcr = librosa.feature.zero_crossing_rate(y)
        avg_zcr = float(np.mean(zcr))

        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
        avg_spectral = float(np.mean(spectral_centroids))


        energy_normalized = min(energy * 100, 50) / 50  # Normalize 0-1
        pitch_stability = 1.0 - min(abs(avg_pitch - 150) / 300, 1.0)  # Around 150Hz is average
        tempo_normalized = min(tempo / 180, 1.0)  # Normal speaking tempo

        confidence_score = (energy_normalized * 0.4) + (pitch_stability * 0.3) + (tempo_normalized * 0.3)
        confidence_score = min(confidence_score, 1.0)

        return {
            'pitch': round(avg_pitch, 2),
            'energy': round(energy, 4),
            'tempo': round(tempo, 2),
            'zero_crossing_rate': round(avg_zcr, 4),
            'spectral_centroid': round(avg_spectral, 2),
            'confidence_score': round(confidence_score, 2)
        }

    except Exception as e:
        logger.error(f"Voice analysis error: {e}")
        return {
            'pitch': 0,
            'energy': 0,
            'tempo': 0,
            'zero_crossing_rate': 0,
            'spectral_centroid': 0,
            'confidence_score': 0,
            'error': str(e)
        }


def full_voice_analysis(audio_file_path, whisper_model='base'):

    # Get transcription
    transcription = speech_to_text(audio_file_path, whisper_model)

    # Get voice features
    voice_features = analyze_voice_features(audio_file_path)

    return {
        'transcription': transcription,
        'voice_features': voice_features,
        'timestamp': str(np.datetime64('now'))
    }


def get_confidence_level(score):

    if score >= 0.7:
        return 'High Confidence'
    elif score >= 0.4:
        return 'Moderate Confidence'
    else:
        return 'Low Confidence'