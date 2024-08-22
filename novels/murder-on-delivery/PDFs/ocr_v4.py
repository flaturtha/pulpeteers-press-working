from pdfminer.high_level import extract_text

# Define the input PDF file name and output text file name
pdf_filename = 'murder_on_delivery.pdf'
txt_filename = 'murder_on_delivery.txt'

# Extract text from the PDF file
text = extract_text(pdf_filename)

# Write the extracted text to a .txt file
with open(txt_filename, 'w', encoding='utf-8') as txt_file:
    txt_file.write(text)

print(f"Text extracted and saved as {txt_filename}")

