

import os
import logging

logger = logging.getLogger('ai_recruitment')

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("ultralytics not available. Phone/notes detection disabled.")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available. Proctoring video processing disabled.")


FLAGGED_CLASSES = {
    'cell phone': 'phone',
    'book': 'notes',
    'laptop': 'second_screen',
    'tv': 'second_screen',
    'remote': 'other_device',
}

_yolo_model = None
_face_cascade = None


def _get_yolo():
    global _yolo_model
    if _yolo_model is None and YOLO_AVAILABLE:
        try:
            _yolo_model = YOLO('yolov8n.pt')
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
    return _yolo_model


def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None and OPENCV_AVAILABLE:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def analyze_frame_proctoring(frame, conf_threshold=0.4):
    """Run object + face detection on a single BGR frame."""
    result = {
        'phone_detected': False,
        'notes_detected': False,
        'other_device_detected': False,
        'face_count': 0,
        'detections': [],
    }

    model = _get_yolo()
    if model is not None:
        try:
            preds = model.predict(frame, verbose=False, conf=conf_threshold)
            for r in preds:
                names = r.names
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    label = names.get(cls_id, str(cls_id))
                    conf = float(box.conf[0])
                    if label in FLAGGED_CLASSES:
                        tag = FLAGGED_CLASSES[label]
                        result['detections'].append({'label': label, 'confidence': round(conf, 3)})
                        if tag == 'phone':
                            result['phone_detected'] = True
                        elif tag == 'notes':
                            result['notes_detected'] = True
                        else:
                            result['other_device_detected'] = True
        except Exception as e:
            logger.error(f"YOLO inference error: {e}")

    cascade = _get_face_cascade()
    if cascade is not None:
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            result['face_count'] = len(faces)
        except Exception as e:
            logger.error(f"Face detection error: {e}")

    return result


def analyze_video_proctoring(video_path, sample_interval=1.0):

    if not OPENCV_AVAILABLE:
        return {'error': 'OpenCV not installed', 'flags': [], 'clean': True}

    if not os.path.exists(video_path):
        return {'error': 'Video file not found', 'flags': [], 'clean': True}

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_interval = max(int(fps * sample_interval), 1)

    frame_count = 0
    samples = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            samples.append(analyze_frame_proctoring(frame))
        frame_count += 1

    cap.release()

    if not samples:
        return {'error': 'No frames analyzed', 'flags': [], 'clean': True}

    total = len(samples)
    phone_ratio = sum(1 for s in samples if s['phone_detected']) / total
    notes_ratio = sum(1 for s in samples if s['notes_detected']) / total
    other_device_ratio = sum(1 for s in samples if s['other_device_detected']) / total
    no_face_ratio = sum(1 for s in samples if s['face_count'] == 0) / total
    multi_face_ratio = sum(1 for s in samples if s['face_count'] > 1) / total

    flags = []
    if phone_ratio > 0.15:
        flags.append('phone_visible')
    if notes_ratio > 0.15:
        flags.append('notes_or_paper_visible')
    if other_device_ratio > 0.15:
        flags.append('second_screen_visible')
    if no_face_ratio > 0.4:
        flags.append('candidate_not_visible')
    if multi_face_ratio > 0.15:
        flags.append('multiple_people_detected')

    return {
        'frames_analyzed': total,
        'phone_ratio': round(phone_ratio, 3),
        'notes_ratio': round(notes_ratio, 3),
        'other_device_ratio': round(other_device_ratio, 3),
        'no_face_ratio': round(no_face_ratio, 3),
        'multiple_faces_ratio': round(multi_face_ratio, 3),
        'flags': flags,
        'clean': len(flags) == 0,
    }