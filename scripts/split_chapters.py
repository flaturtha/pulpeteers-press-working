import re
import os

# Prompt for the markdown file path
markdown_file_path = input("Enter the path to the markdown file: ")

# Read the entire markdown file
try:
    with open(markdown_file_path, 'r') as file:
        content = file.read()
except Exception as e:
    print(f"Error reading file: {e}")
    exit(1)

# Adjusted regex to match "Chapter" followed by any title
try:
    chapter_splits = re.split(r'(### Chapter [^\n]+)', content)
    print(f"Split content into {len(chapter_splits)//2} chapters.")
except Exception as e:
    print(f"Error splitting content: {e}")
    exit(1)

# Combine the split results into chapter contents
chapters = ["".join(chapter_splits[i:i+2]) for i in range(1, len(chapter_splits), 2)]

# Create the output directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(markdown_file_path), 'chapters')
os.makedirs(output_dir, exist_ok=True)

# Save each chapter into a separate markdown file
for chapter in chapters:
    match = re.search(r'### Chapter (\d+)', chapter)
    if match:
        chapter_num = match.group(1)
        print(f"Processing Chapter {chapter_num}")
        output_file_path = os.path.join(output_dir, f'ch{chapter_num}.md')
        try:
            with open(output_file_path, 'w') as file:
                file.write(chapter)
            print(f"Chapter {chapter_num} written to {output_file_path}")
        except Exception as e:
            print(f"Error writing chapter {chapter_num}: {e}")
    else:
        print("No chapter match found in the current split.")

print(f"Chapters have been successfully split into separate files in the '{output_dir}' directory.")

