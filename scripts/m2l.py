import os
import re
import yaml
import unicodedata

def read_template(template_path):
    with open(template_path, 'r') as file:
        return file.read()

def read_frontmatter(frontmatter_path):
    with open(frontmatter_path, 'r') as file:
        return list(yaml.safe_load_all(file))[0]

def read_chapter(chapter_path):
    with open(chapter_path, 'r') as file:
        return file.read()

def process_chapters(chapters_dir):
    chapters = []
    for filename in sorted(os.listdir(chapters_dir)):
        if filename.endswith('.md') and filename != 'frontmatter.yml':
            chapter_path = os.path.join(chapters_dir, filename)
            chapter_content = read_chapter(chapter_path)
            chapter_num = filename.split('.')[0]
            first_line, rest_of_content = chapter_content.split('\n', 1)
            chapters.append({
                'number': chapter_num,
                'first_line': first_line.strip(),
                'content': rest_of_content.strip()
            })
    print(f"Processed {len(chapters)} chapters")
    return chapters

def generate_latex(template, frontmatter, chapters):
    latex_content = template

    # Existing replacements
    latex_content = latex_content.replace('TITLE', frontmatter.get('title', ''))
    latex_content = latex_content.replace('AUTHOR', frontmatter.get('author', ''))
    latex_content = latex_content.replace('GENRE', frontmatter.get('genre', ''))
    latex_content = latex_content.replace('PUBLICATION_DATE', frontmatter.get('original_publication', ''))
    latex_content = latex_content.replace('O_PUB', frontmatter.get('publisher', ''))

    # Generate table of contents
    toc_content = ''
    for num in frontmatter.get('chapters', []):
        toc_content += f"\\tocitem*[{num}]{{{num}}}{{{num}}}\n"
    latex_content = latex_content.replace('%TOC_ENTRIES%', toc_content)

    # Chapter content replacement
    chapters_content = ''
    for chapter in chapters:
        chapter_text = chapter['content'].split('\n', 1)
        first_line = chapter_text[0].strip()
        chapters_content += f"""
\\begin{{ChapterStart}}
\\vspace{{3\\nbs}}
\\ChapterSubtitle[l]{{Chapter {chapter['number']}}}
\\ChapterTitle[l]{{{chapter['number']}}}
\\end{{ChapterStart}}
\\FirstLine{{\\noindent {first_line}}}
    {chapter_text[1] if len(chapter_text) > 1 else ''}

\\vspace{{2\\nbs}}
\\ChapterDeco[c1]{{\\decoglyph{{e9665}}}}
\\clearpage
\\thispagestyle{{empty}}
"""

    latex_content = latex_content.replace('%CHAPTER_CONTENT%', chapters_content)

    return latex_content

def clean_filename(title):
    # Normalize unicode characters
    title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('ASCII')
    
    # Replace spaces and underscores with a single underscore
    title = re.sub(r'[\s_]+', '_', title)
    
    # Remove any non-alphanumeric characters except underscores
    title = re.sub(r'[^\w\-]', '', title)
    
    # Remove leading/trailing underscores
    title = title.strip('_')
    
    # Ensure the filename is not empty
    if not title:
        title = "untitled"
    
    return title.lower()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    
    template_path = os.path.join(base_dir, 'Tales_of_Murder', '2024', 'templates', 'template.tex')
    print(f"Template path: {template_path}")
    
    chapters_dir = input("Enter the path to the chapters directory (default: current directory): ").strip()
    if not chapters_dir:
        chapters_dir = os.getcwd()
    print(f"Chapters directory: {chapters_dir}")
    
    frontmatter_path = os.path.join(chapters_dir, 'frontmatter.yml')
    print(f"Frontmatter path: {frontmatter_path}")
    
    frontmatter = read_frontmatter(frontmatter_path)
    default_output_file = f"{clean_filename(frontmatter.get('title', 'output'))}.tex"
    
    output_file = input(f"Enter the name of the output LaTeX file (default: {default_output_file}): ").strip()
    if not output_file:
        output_file = default_output_file

    template = read_template(template_path)
    chapters = process_chapters(chapters_dir)

    latex_content = generate_latex(template, frontmatter, chapters)

    with open(output_file, 'w') as file:
        file.write(latex_content)

    print(f"LaTeX file generated: {output_file}")
    print(f"Output file size: {os.path.getsize(output_file)} bytes")

if __name__ == "__main__":
    main()
