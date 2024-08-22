import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import os

def advanced_preprocess_image(image):
    print("Preprocessing image...")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Refined cropping
    height, width = gray.shape
    crop_top = int(height * 0.115)  # Crop 11.5% from top
    crop_bottom = int(height * 0.07)  # Crop 7% from bottom
    crop_left = int(width * 0.1)  # Crop 10% from left
    crop_right = int(width * 0.1)  # Crop 10% from right
    cropped = gray[crop_top:height-crop_bottom, crop_left:width-crop_right]
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contrast = clahe.apply(cropped)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(contrast, None, 10, 7, 21)
    
    # Binarization
    binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # Dilation to connect nearby text components
    kernel = np.ones((1,1), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    
    print("Image preprocessing complete.")
    return dilated# Create 'processed' subfolder if it doesn't exist
os.makedirs('processed', exist_ok=True)

# Ask for PDF path
pdf_path = input("Please enter the path to your PDF file: ")
print(f"Processing PDF: {pdf_path}")
import sys
try:
    # Convert PDF to images
    print("Converting PDF to images...")
    pages = convert_from_path(pdf_path, 600, first_page=1, last_page=None, thread_count=1)
    print(f"Converted {len(pages)} pages to images.")

    # Process each page
    processed_pages = []
    for page_num, page in enumerate(pages, start=1):
        print(f"Processing page {page_num} of {len(pages)}...")
        image = np.array(page)
        processed_image = advanced_preprocess_image(image)
        processed_pages.append(processed_image)
        cv2.imwrite(f'processed/preprocessed_page_{page_num}.png', processed_image)
        print(f"Saved preprocessed image for page {page_num}")

    # Perform OCR on Preprocessed Images
    print("Performing OCR on preprocessed images...")
    extracted_text = ""
    for page_num, page_image in enumerate(processed_pages, start=1):
        print(f"Extracting text from page {page_num} of {len(processed_pages)}...")
        # Rest of the OCR code...
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
# Perform OCR on Preprocessed Images
print("Performing OCR on preprocessed images...")
extracted_text = ""
for page_num, page_image in enumerate(processed_pages, start=1):
    print(f"Extracting text from page {page_num} of {len(processed_pages)}...")
    # Try different OCR configurations
    text1 = pytesseract.image_to_string(page_image, lang='eng', config='--psm 6')
    text2 = pytesseract.image_to_string(page_image, lang='eng', config='--psm 3')
    text = text1 if len(text1) > len(text2) else text2
    extracted_text += f"--- Page {page_num} ---\n{text}\n"

# Save the extracted text to a file
output_file = 'processed/improved_extracted_text.txt'
print(f"Saving extracted text to {output_file}...")
with open(output_file, 'w', encoding='utf-8') as text_file:
    text_file.write(extracted_text)

print(f"Text extraction complete. Check '{output_file}' for the output.")
