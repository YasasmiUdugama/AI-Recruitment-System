

import os
import logging
import json

logger = logging.getLogger('ai_recruitment')

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    logger.warning("DeepFace not available. Emotion detection disabled.")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available. Video processing disabled.")

# Emotion mapping for analysis
EMOTION_CATEGORIES = {
    'positive': ['happy', 'surprise'],
    'negative': ['angry', 'disgust', 'fear', 'sad'],
    'neutral': ['neutral']
}


def analyze_image_emotions(image_path):

    if not DEEPFACE_AVAILABLE or not OPENCV_AVAILABLE:
        logger.warning("DeepFace or OpenCV not available for emotion detection")
        return {
            'dominant_emotion': 'unknown',
            'emotions': {},
            'face_confidence': 0,
            'category': 'unknown',
            'error': 'DeepFace or OpenCV not installed'
        }

    if not os.path.exists(image_path):
        return {
            'dominant_emotion': 'unknown',
            'emotions': {},
            'face_confidence': 0,
            'category': 'unknown',
            'error': 'Image file not found'
        }

    try:
        # Analyze emotions using DeepFace
        result = DeepFace.analyze(
            img_path=image_path,
            actions=['emotion'],
            enforce_detection=False,
            silent=True
        )

        if isinstance(result, list) and len(result) > 0:
            result = result[0]

        emotion_data = result.get('emotion', {})
        dominant_emotion = result.get('dominant_emotion', 'unknown')
        face_confidence = result.get('face_confidence', 0)

        # Normalize emotion scores to 0-1 range
        total = sum(emotion_data.values()) if emotion_data else 1
        normalized_emotions = {
            k: round(v / total, 4) for k, v in emotion_data.items()
        } if total > 0 else emotion_data

        # Determine category
        category = 'neutral'
        if dominant_emotion in EMOTION_CATEGORIES['positive']:
            category = 'positive'
        elif dominant_emotion in EMOTION_CATEGORIES['negative']:
            category = 'negative'

        return {
            'dominant_emotion': dominant_emotion,
            'emotions': normalized_emotions,
            'face_confidence': round(float(face_confidence), 4),
            'category': category
        }

    except Exception as e:
        logger.error(f"Emotion analysis error: {e}")
        return {
            'dominant_emotion': 'unknown',
            'emotions': {},
            'face_confidence': 0,
            'category': 'unknown',
            'error': str(e)
        }


def analyze_video_emotions(video_path, sample_interval=1.0):
    if not DEEPFACE_AVAILABLE or not OPENCV_AVAILABLE:
        return {
            'error': 'DeepFace or OpenCV not installed',
            'dominant_emotion': 'unknown',
            'emotion_timeline': []
        }

    if not os.path.exists(video_path):
        return {
            'error': 'Video file not found',
            'dominant_emotion': 'unknown',
            'emotion_timeline': []
        }

    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * sample_interval)

        emotion_timeline = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                # Save frame temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    cv2.imwrite(tmp.name, frame)
                    frame_path = tmp.name

                try:
                    result = analyze_image_emotions(frame_path)
                    if 'error' not in result or not result['error']:
                        emotion_timeline.append({
                            'frame': frame_count,
                            'timestamp': round(frame_count / fps, 2),
                            'emotion': result['dominant_emotion'],
                            'confidence': result['face_confidence'],
                            'category': result['category']
                        })
                except:
                    pass
                finally:
                    os.unlink(frame_path)

            frame_count += 1

        cap.release()

        # Aggregate results
        if emotion_timeline:
            emotion_counts = {}
            for entry in emotion_timeline:
                emotion = entry['emotion']
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

            dominant_emotion = max(emotion_counts, key=emotion_counts.get)

            # Calculate positive emotion ratio
            positive_count = sum(1 for e in emotion_timeline if e['category'] == 'positive')
            positive_ratio = positive_count / len(emotion_timeline)

            return {
                'dominant_emotion': dominant_emotion,
                'emotion_distribution': emotion_counts,
                'positive_ratio': round(positive_ratio, 4),
                'total_frames_analyzed': len(emotion_timeline),
                'emotion_timeline': emotion_timeline[:50]  # Limit stored timeline
            }
        else:
            return {
                'error': 'No faces detected in video',
                'dominant_emotion': 'unknown',
                'emotion_timeline': []
            }

    except Exception as e:
        logger.error(f"Video emotion analysis error: {e}")
        return {
            'error': str(e),
            'dominant_emotion': 'unknown',
            'emotion_timeline': []
        }


def get_emotion_summary(emotion_data):

    if 'error' in emotion_data and emotion_data['error']:
        return f"Emotion analysis unavailable: {emotion_data['error']}"

    dominant = emotion_data.get('dominant_emotion', 'unknown')
    positive_ratio = emotion_data.get('positive_ratio', 0)

    if positive_ratio >= 0.6:
        demeanor = "positive and engaged demeanor"
    elif positive_ratio >= 0.3:
        demeanor = "generally neutral demeanor"
    else:
        demeanor = "reserved or serious demeanor"

    return f"Dominant emotion: {dominant}. Candidate showed a {demeanor} during the interview."


def calculate_emotion_score(emotion_data):

    if 'error' in emotion_data and emotion_data['error']:
        return 0.5  # Default neutral score

    positive_ratio = emotion_data.get('positive_ratio', 0.5)

    # Map positive ratio to score
    # 0.0 -> 0.2, 0.5 -> 0.6, 1.0 -> 1.0
    score = 0.2 + (positive_ratio * 0.8)

    return round(min(score, 1.0), 2)
