import os
from spellchecker import SpellChecker

# Initialize spell checker
spell = SpellChecker()

def correct_text(text):
    words = text.split()
    corrected_text = ' '.join([spell.correction(word) or word for word in words])
    return corrected_text

# Prompt the user for the input file path
input_file_path = input("Please enter the path to the text file to post-process: ")

# Check if the provided path exists and is a file
if not os.path.isfile(input_file_path):
    print(f"The path '{input_file_path}' is not a valid file. Please check the path and try again.")
else:
    # Load extracted text
    with open(input_file_path, 'r', encoding='utf-8') as file:
        extracted_text = file.read()

    # Apply corrections
    corrected_text = correct_text(extracted_text)

    # Define output file path by appending '_corrected.md' to the original file name
    base_name, ext = os.path.splitext(input_file_path)
    corrected_output_file = f"{base_name}_corrected.md"

    # Save the corrected text to a new file
    with open(corrected_output_file, 'w', encoding='utf-8') as text_file:
        text_file.write(corrected_text)

    print(f"Text correction complete. Check '{corrected_output_file}' for the output.")

