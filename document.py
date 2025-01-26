"""
Title: Document PII Masking
Author: Mayank Harlalka
Date: 05-10-2024
Description: Detects PII in documents using OCR, GLiNER, SpaCy, and Regex, then masks it by drawing black rectangles. It accepts a doccument path and saves the masked document to a provided path.
"""

# Import necessary libraries
import easyocr
import cv2
import sys
from gliner import GLiNER
from fpdf import FPDF
import pypdfium2
from common_functions import draw_black_rectangles

def main(pdf_path, labels, output_pdf_path):
    # Load GLiNER model for PII detection
    model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
    pdf = pypdfium2.PdfDocument(pdf_path)    
    processed_images = []
    # Initialize EasyOCR reader for text extraction
    reader = easyocr.Reader(['en'])
    for i in range(len(pdf)):
        page = pdf[i]
        image = page.render(scale=4).to_pil()
        image.save(f"output_{i:03d}.jpg")

        original_image = cv2.imread(f'output_{i:03d}.jpg')
        result = reader.readtext(f'output_{i:03d}.jpg', width_ths=0.5)

        processed_image = original_image.copy()
        draw_black_rectangles(processed_image, result, labels, model)

        processed_images.append(processed_image)

        # # Display the modified image (optional)
        # combined_image = np.hstack((original_image, processed_image))
        # cv2.imshow(combined_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

    # Create a new PDF with the processed images
    pdf_writer = FPDF()

    for img in processed_images:
        img_path = "temp_page.jpg"
        cv2.imwrite(img_path, img)
        pdf_writer.add_page()
        pdf_writer.image(img_path, 0, 0, 210, 297)  # Adjust dimensions (210x297 mm) to match A4 size

    return pdf_writer.output(output_pdf_path)  

     
 

if __name__ == "__main__":
    try:
        input_pdf_path = 'path'
        output_pdf_path = 'path'
        labels = ["name", "ip_address", "email", "phone number"]
        redacted_pdf = main(input_pdf_path, labels, output_pdf_path)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
