"""
Title: PII Masking in Texts
Author: Mayank Harlalka
Date: 05-10-2024
Description: Detection and Masking of PII Elements in Text Inputs. It accepts a string input and returns the masked text.
"""

# Import necessary libraries
from gliner import GLiNER
import sys
from common_functions import redact_pii
# Load the GLiNER model
model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")



def main(text, labels): 
    
    # Redact the PII from the document
    redacted_document = redact_pii(text, labels, model)
    return redacted_document



if __name__ == "__main__":
    try:
        # Sample input text
        text = "John Doe's SSN is 123-45-6789 and his phone number is +1-555-555-5555. His PAN Number is ABCDE1234F."
        # Placeholder for the model's entity prediction
        labels = ["work", "booking number", "personally identifiable information", "social security number", "driver licence", "book", "full address", "company", "actor", "character", "email", "passport number", "Social Security Number", "phone number"]
        redacted_output = main(text, labels)
        print("Redacted Text:\n", redacted_output)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)