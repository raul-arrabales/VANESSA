from __future__ import annotations

SERVICE_VERSION = "0.1.0"
DEFAULT_PORT = 8090
DEFAULT_CAPTION_MODEL_ID = "florence-community/Florence-2-base-ft"

TASK_LICENSE_PLATE_RECOGNITION = "license_plate_recognition"
TASK_OBJECT_DETECTION = "object_detection"
TASK_CAPTIONING = "captioning"
VALID_TASKS = {TASK_LICENSE_PLATE_RECOGNITION, TASK_OBJECT_DETECTION, TASK_CAPTIONING}

ROLE_GATEWAY = "gateway"
ROLE_ANPR = "anpr"
ROLE_OBJECTS = "objects"
ROLE_CAPTIONING = "captioning"
VALID_ROLES = {ROLE_GATEWAY, ROLE_ANPR, ROLE_OBJECTS, ROLE_CAPTIONING}

ROLE_TASKS = {
    ROLE_ANPR: {TASK_LICENSE_PLATE_RECOGNITION},
    ROLE_OBJECTS: {TASK_OBJECT_DETECTION},
    ROLE_CAPTIONING: {TASK_CAPTIONING},
}
TASK_ROLE = {
    TASK_LICENSE_PLATE_RECOGNITION: ROLE_ANPR,
    TASK_OBJECT_DETECTION: ROLE_OBJECTS,
    TASK_CAPTIONING: ROLE_CAPTIONING,
}

COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]
