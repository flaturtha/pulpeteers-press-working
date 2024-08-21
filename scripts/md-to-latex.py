import os
import re
import yaml

# Define paths
directory_path = '/run/media/h/T7 Shield/dox/2_Pulpeteers-Press/Tales of Murder/2024/novels/spider-lily/md/chapters/'
latex_template_file = '/run/media/h/T7 Shield/dox/2_Pulpeteers-Press/Tales of Murder/2024/LaTeX experiments/template.tex'
output_file = '/run/media/h/T7 Shield/dox/2_Pulpeteers-Press/Tales of Murder/2024/novels/spider-lily/Latex/output_combined.tex'
frontmatter_file = '/run/media/h/T7 Shield/dox/2_Pulpeteers-Press/Tales of Murder/2024/novels/spider-lily/md/chapters/frontmatter.yml'

def extract_values_from_file(file_path):
    values = {}
    body_text = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            match_num = re.match(r'\.ch-num\s*=\s*(.*)\s*{\.ch-num}', line)
            match_name = re.match(r'\.ch-name\s*=\s*(.*)\s*{\.ch-name}', line)
            if match_num:
                values['CHAPTER_NUM'] = match_num.group(1).strip()
            elif match_name:
                values['CHAPTER_NAME'] = match_name.group(1).strip()
            else:
                body_text.append(line.strip())
    values['CHAPTER_BODY'] = "\n".join(body_text).strip()
    return values

def load_frontmatter():
    with open(frontmatter_file, 'r') as f:
        return list(yaml.safe_load_all(f))

def main():
    with open(latex_template_file, 'r') as f:
        latex_template = f.read()

    frontmatter = load_frontmatter()
    final_latex_content = ""
    md_file_count = 0

    for filename in sorted(os.listdir(directory_path)):
        if filename.endswith('.md'):
            md_file_count += 1
            file_path = os.path.join(directory_path, filename)
            values = extract_values_from_file(file_path)
            
            print(f"Processing {filename}")
            print("Extracted Values:")
            for key, value in values.items():
                print(f"{key}: {value}")
            
            chapter_content = latex_template
            for key, value in values.items():
                chapter_content = chapter_content.replace(key.upper(), value)
            
            for frontmatter_doc in frontmatter:
                for key, value in frontmatter_doc.items():
                    chapter_content = chapter_content.replace(key.upper(), str(value))
            
            final_latex_content += chapter_content + "\n"

    with open(output_file, 'w') as f:
        f.write(final_latex_content)

    print(f'Total .md files processed: {md_file_count}')
    print(f'Updated LaTeX file has been saved as {output_file}')

if __name__ == "__main__":
    main()
