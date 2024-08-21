import os
import re

def read_template(template_path):
    with open(template_path, 'r') as file:
        return file.read()

def read_chapter(chapter_path):
    with open(chapter_path, 'r') as file:
        return file.read()

def extract_chapter_info(chapter_content):
    # Extract chapter number and title (assuming they're in the first few lines)
    lines = chapter_content.split('\n')
    chapter_num = None
    chapter_title = None
    for line in lines[:10]:
        if 'Chapter' in line:
            match = re.search(r'Chapter (\d+)', line)
            if match:
                chapter_num = match.group(1)
        elif line.strip() and not chapter_title:
            chapter_title = line.strip()
        if chapter_num and chapter_title:
            break
    return chapter_num, chapter_title, '\n'.join(lines)

def generate_latex_chapter(template, chapter_info):
    chapter_num, chapter_title, chapter_content = chapter_info
    latex_content = template.replace('CHAPTER_NUM', chapter_num)
    latex_content = latex_content.replace('CHAPTER_NAME', chapter_title)
    latex_content = latex_content.replace('CHAPTER_BODY', chapter_content)
    return latex_content

def main():
    template_path = 'template.tex'
    chapters_dir = 'chapters'
    output_dir = 'output'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    template = read_template(template_path)

    for filename in sorted(os.listdir(chapters_dir)):
        if filename.endswith('.md'):
            chapter_path = os.path.join(chapters_dir, filename)
            chapter_content = read_chapter(chapter_path)
            chapter_info = extract_chapter_info(chapter_content)
            latex_chapter = generate_latex_chapter(template, chapter_info)

            output_filename = f'chapter_{chapter_info[0]}.tex'
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, 'w') as file:
                file.write(latex_chapter)

            print(f'Generated {output_filename}')

if __name__ == '__main__':
    main()
