import os
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract

def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Remove noise
    denoised = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Morphological operations to improve text structure
    kernel = np.ones((1, 1), np.uint8)
    morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Deskew image
    coords = np.column_stack(np.where(morphed > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = morphed.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(morphed, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return deskewed

# Prompt the user for the PDF path
pdf_path = input("Please enter the path to the PDF file: ")

# Check if the provided path exists and is a file
if not os.path.isfile(pdf_path):
    print(f"The path '{pdf_path}' is not a valid file. Please check the path and try again.")
else:
    # Extract the directory and filename
    pdf_dir = os.path.dirname(pdf_path)
    pdf_filename = os.path.basename(pdf_path)
    pdf_basename = os.path.splitext(pdf_filename)[0]

    # Create 'mds' directory if it doesn't exist
    mds_dir = os.path.join(pdf_dir, 'mds')
    os.makedirs(mds_dir, exist_ok=True)

    # Define output file path
    output_md_path = os.path.join(mds_dir, f"{pdf_basename}.md")

    # Convert PDF to a list of images
    pages = convert_from_path(pdf_path, 300)  # 300 is the DPI (dots per inch)

    # Initialize a variable to hold the text
    extracted_text = ""

    # Process each page
    for page_num, page in enumerate(pages, start=1):
        image = np.array(page)
        processed_image = preprocess_image(image)
        
        # Use pytesseract to do OCR on the page image
        text = pytesseract.image_to_string(processed_image, lang='eng')
        
        # Append the page text to the extracted_text variable
        extracted_text += f"## Page {page_num}\n{text}\n"

    # Save the extracted text to a Markdown file
    with open(output_md_path, 'w', encoding='utf-8') as md_file:
        md_file.write(extracted_text)

    print(f"Text extraction complete. Check '{output_md_path}' for the output.")

