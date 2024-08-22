import PyPDF2
import yaml
import re

def extract_pdf_info(pdf_path, num_pages=3):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for i in range(min(num_pages, len(reader.pages))):
            text += reader.pages[i].extract_text()
    return text

def parse_info(text):
    info = {}
    info['title'] = re.search(r'(?:BRAND OF SILENCE|THE BRAND OF SILENCE)', text, re.IGNORECASE)
    info['author'] = re.search(r'by\s+([\w\s]+)', text, re.IGNORECASE)
    info['publisher'] = re.search(r'Tales of Murder Publishing', text, re.IGNORECASE)
    info['genre'] = "Mystery"  # Assuming based on the content
    info['original_publication'] = None  # We don't have this information in the extracted text
    info['isbn'] = None  # We don't have this information in the extracted text

    copyright_match = re.search(r'Copyright\s+([\d]{4})\s+by\s+([\w\s]+)', text, re.IGNORECASE)
    if copyright_match:
        info['copyright'] = {
            'status': 'Copyright',
            'additional_elements': f"Copyright {copyright_match.group(1)} by {copyright_match.group(2)}"
        }
    else:
        info['copyright'] = {
            'status': 'Public Domain',
            'additional_elements': ''
        }

    chapters = re.findall(r'(\d+)\s+(.*)', text)
    info['chapters'] = {num: title.strip() for num, title in chapters if title.strip()}

    return {k: v.group() if isinstance(v, re.Match) else v for k, v in info.items()}

def create_frontmatter(info, output_path):
    with open(output_path, 'w') as file:
        yaml.dump(info, file, default_flow_style=False, sort_keys=False)

def main():
    pdf_path = input("Enter the path to your PDF file: ")
    output_path = "frontmatter.yml"
    text = extract_pdf_info(pdf_path, num_pages=10)  # Increased to 10 pages
    print("Extracted text:")
    print(text[:1000])  # Print first 1000 characters
    info = parse_info(text)
    create_frontmatter(info, output_path)
    print(f"Frontmatter has been created at {output_path}")

if __name__ == "__main__":
    main()
