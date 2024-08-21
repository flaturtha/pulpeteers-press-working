import cv2
import numpy as np
from pdf2image import convert_from_path

def advanced_preprocess_image(image):
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

# Convert PDF to images
pdf_path = 'path/to/your/file.pdf'
pages = convert_from_path(pdf_path, 300)

# Process each page
processed_pages = []
for page_num, page in enumerate(pages, start=1):
    image = np.array(page)
    processed_image = advanced_preprocess_image(image)
    processed_pages.append(processed_image)
    # Save the preprocessed image for inspection
    cv2.imwrite(f'preprocessed_page_{page_num}.png', processed_image)

# Perform OCR on Preprocessed Images
extracted_text = ""
for page_num, page_image in enumerate(processed_pages, start=1):
    text = pytesseract.image_to_string(page_image, lang='eng')
    extracted_text += f"--- Page {page_num} ---\n{text}\n"

# Save the extracted text to a file
output_file = 'improved_extracted_text.txt'
with open(output_file, 'w', encoding='utf-8') as text_file:
    text_file.write(extracted_text)

print(f"Text extraction complete. Check '{output_file}' for the output.")

