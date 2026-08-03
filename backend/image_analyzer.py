from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image
    import numpy as np
except ImportError:
    Image = None
    np = None


def analyze_image(image_path: str) -> dict:
    if cv2 is not None:
        image = cv2.imread(image_path)
        if image is None:
            return {
                "summary": "Unable to read uploaded image.",
                "space_type": "Unknown",
                "sunlight": "Moderate",
                "soil_condition": "Unknown",
            }
        height, width = image.shape[:2]
        brightness = image.mean()
    elif Image is not None and np is not None:
        try:
            image = Image.open(Path(image_path)).convert("RGB")
            arr = np.asarray(image)
            height, width = arr.shape[:2]
            brightness = float(arr.mean())
        except Exception:
            return {
                "summary": "Unable to read uploaded image.",
                "space_type": "Unknown",
                "sunlight": "Moderate",
                "soil_condition": "Unknown",
            }
    else:
        return {
            "summary": "Unable to read uploaded image. Missing cv2 or Pillow.",
            "space_type": "Unknown",
            "sunlight": "Moderate",
            "soil_condition": "Unknown",
        }

    if width > height:
        space_type = "Lawn"
    elif height > width and height / width > 1.2:
        space_type = "Balcony"
    else:
        space_type = "Rooftop"

    if brightness > 140:
        sunlight = "Full Sun"
    elif brightness > 100:
        sunlight = "Partial Sun"
    else:
        sunlight = "Shade"

    soil_condition = "Dry" if sunlight == "Full Sun" else "Moist"
    return {
        "summary": f"Detected {space_type} style space with {sunlight}, estimated soil as {soil_condition}.",
        "space_type": space_type,
        "sunlight": sunlight,
        "soil_condition": soil_condition,
    }
