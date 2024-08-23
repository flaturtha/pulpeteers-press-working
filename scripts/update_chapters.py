import os
import re

def read_chapter_titles(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    titles = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and line.isdigit():
            chapter_num = int(line)
            if i + 1 < len(lines):
                title = lines[i + 1].strip()
                titles[chapter_num] = title
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    print(f"Read {len(titles)} chapter titles")
    for num, title in titles.items():
        print(f"Chapter {num}: {title}")
    return titles

def update_main_document(main_file, titles, output_file):
    with open(main_file, 'r') as f:
        content = f.read()
    
    def replace_chapter(match):
        chapter_num = int(match.group(1))
        if chapter_num in titles:
            print(f"Updating Chapter {chapter_num}")
            return f"### Chapter {chapter_num}\n## {titles[chapter_num]}\n"
        print(f"No title found for Chapter {chapter_num}")
        return match.group(0)
    
    updated_content = re.sub(r'### Chapter (\d+)', replace_chapter, content)
    
    changes_made = content != updated_content
    with open(output_file, 'w') as f:
        f.write(updated_content)
    print(f"Changes made: {changes_made}")
    print(f"Updated content written to {output_file}")

script_dir = os.path.dirname(os.path.abspath(__file__))
chapter_titles_path = os.path.join(script_dir, 'chapter-titles.md')
main_file_path = os.path.join(script_dir, 'corpse-steps-out.md')
output_file_path = os.path.join(script_dir, 'corpse-steps-out-updated.md')

chapter_titles = read_chapter_titles(chapter_titles_path)
update_main_document(main_file_path, chapter_titles, output_file_path)