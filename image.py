"""
Title: Image PII Masking
Author: Mayank Harlalka
Date: 05-10-2024
Description: Detects PII in images using OCR, GLiNER, SpaCy, and Regex, then masks it by drawing black rectangles. It accepts an image path and returns the masked image.
"""

# Import necessary libraries
import easyocr
import cv2
import sys
import numpy as np
from gliner import GLiNER
from common_functions import draw_black_rectangles



def main(image_path, labels):
    # Load GLiNER model for PII detection
    model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")

    # Initialize EasyOCR reader for text extraction
    reader = easyocr.Reader(['en'])

    original_image = cv2.imread(image_path)
    result = reader.readtext(image_path, width_ths=0.5)
    processed_image = original_image.copy()

    
    draw_black_rectangles(processed_image, result, labels, model)

    return processed_image

if __name__ == "__main__":
    try:
        sample_image = 'path'
        labels = ["name", "ip_address", "email", "phone number"]
        redacted_image = main(sample_image, labels)

        ##Optional
        # combined_image = np.hstack((cv2.imread(sample_image), redacted_image))
        # cv2.imshow('Original vs Redacted', combined_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)