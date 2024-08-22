from openai import OpenAI
import tiktoken
import re

client = OpenAI(api_key='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')

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def clean_text_chunk(chunk):
    # Remove page marker text
    chunk = re.sub(r'--- Page \d+ ---\n', '', chunk)

    # Replace single newlines with spaces, but keep double newlines
    chunk = re.sub(r'(?<!\n)\n(?!\n)', ' ', chunk)

    # Convert all-caps first line of each paragraph to proper capitalization
    chunk = re.sub(r'(?<=\n\n)([A-Z\s]+)(?=\n)', lambda m: m.group(1).capitalize(), chunk)

    prompt = (
        "You are an expert editor specializing in cleaning up text generated from OCR scans of fiction novels. "
        "The text may contain common OCR errors such as misinterpreted characters (e.g., '0' instead of 'O', '1' instead of 'l'), "
        "misspelled words, and random symbols or special characters that don't belong (like '§', '∆', '™', '®'). "
        "Your task is to carefully correct these errors while preserving the original intent and style of the text. "
        "Please ensure that spelling, punctuation, and formatting are consistent with standard novel conventions. "
        "Pay special attention to the first line of each paragraph, ensuring proper capitalization (full names with initial caps, "
        "but otherwise following normal sentence capitalization rules). "
        "Here is the text that needs cleaning:\n\n"
        f"{chunk}\n\n"
        "Please provide the cleaned and corrected text."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert editor specializing in cleaning up OCR-scanned text."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.5
    )

    return response.choices[0].message.content.strip()# Ask for the file to clean
file_path = input("Enter the path to the file you want to clean: ")

# Read the content of the file
with open(file_path, 'r', encoding='utf-8') as file:
    raw_text = file.read()

# Split the text into chunks
chunk_size = 4000  # Adjust this value as needed
chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]

# Process each chunk
cleaned_chunks = []
for i, chunk in enumerate(chunks):
    print(f"Processing chunk {i+1} of {len(chunks)}...")
    cleaned_chunk = clean_text_chunk(chunk)
    cleaned_chunks.append(cleaned_chunk)

# Combine the cleaned chunks
cleaned_text = "\n".join(cleaned_chunks)

# Save the cleaned text to a new file
output_file = 'cleaned_' + file_path.split('/')[-1]
with open(output_file, 'w', encoding='utf-8') as file:
    file.write(cleaned_text)

print(f"Cleaning complete. The cleaned text has been saved to {output_file}")


