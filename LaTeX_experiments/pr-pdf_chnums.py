import re
from PyPDF2 import PdfReader
import os

def extract_chapter_pages(pdf_path):
    reader = PdfReader(pdf_path)
    chapter_pages = {}
    
    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        match = re.search(r'Chapter (\d+)', text)
        if match:
            chapter_num = match.group(1)
            chapter_pages[chapter_num] = page_num
    
    return chapter_pages

def update_toc(template_path, chapter_pages):
    with open(template_path, 'r') as file:
        content = file.read()
    
    toc_pattern = r'\\tocitem\*\[(\d+)\]\{([^}]+)\}\{\d+\}'
    
    def replace_page(match):
        chapter_num = match.group(1)
        chapter_title = match.group(2)
        page_num = chapter_pages.get(chapter_num, '1')
        return f'\\tocitem*[{chapter_num}]{{{chapter_title}}}{{{page_num}}}'
    
    updated_content = re.sub(toc_pattern, replace_page, content)
    
    with open(template_path, 'w') as file:
        file.write(updated_content)

def main():
    pdf_path = 'output.pdf'
    template_path = 'template.tex'
    
    chapter_pages = extract_chapter_pages(pdf_path)
    update_toc(template_path, chapter_pages)
    
    print("Table of contents updated with correct page numbers.")

if __name__ == '__main__':
    main()