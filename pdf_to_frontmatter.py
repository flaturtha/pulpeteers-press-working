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
    info['title'] = re.search(r'Title:\s*(.*)', text, re.IGNORECASE)
    info['author'] = re.search(r'Author:\s*(.*)', text, re.IGNORECASE)
    info['publisher'] = re.search(r'Publisher:\s*(.*)', text, re.IGNORECASE)
    info['genre'] = re.search(r'Genre:\s*(.*)', text, re.IGNORECASE)
    info['original_publication'] = re.search(r'Original Publication:\s*(.*)', text, re.IGNORECASE)
    info['isbn'] = re.search(r'ISBN:\s*(.*)', text, re.IGNORECASE)

    # Extract copyright information
    copyright_match = re.search(r'Copyright:\s*(.*)', text, re.IGNORECASE)
    if copyright_match:
        info['copyright'] = {
            'status': 'Copyright',
            'additional_elements': copyright_match.group(1)
        }
    else:
        info['copyright'] = {
            'status': 'Public Domain',
            'additional_elements': ''
        }

    # Extract chapters
    chapters = re.findall(r'Chapter (\d+):\s*(.*)', text, re.IGNORECASE)
    info['chapters'] = {int(num): title for num, title in chapters}

    return {k: v.group(1) if isinstance(v, re.Match) else v for k, v in info.items()}

def create_frontmatter(info, output_path):
    with open(output_path, 'w') as file:
        yaml.dump(info, file, default_flow_style=False, sort_keys=False)

def main(pdf_path, output_path):
    text = extract_pdf_info(pdf_path)
    info = parse_info(text)
    create_frontmatter(info, output_path)

if __name__ == "__main__":
    pdf_path = "path/to/your/pdf/file.pdf"
    output_path = "frontmatter.yml"
    main(pdf_path, output_path)
