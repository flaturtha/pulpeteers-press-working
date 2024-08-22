import PyPDF2
import markdown

def extract_text_to_markdown(pdf_path, markdown_path):
    """Extracts text from a PDF and saves it as a Markdown file.

    Args:
        pdf_path (str): Path to the PDF file.
        markdown_path (str): Path to save the Markdown file.
    """

    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = ''
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()

    markdown_content = markdown.markdown(text)

    with open(markdown_path, 'w', encoding='utf-8') as markdown_file:
        markdown_file.write(markdown_content)

# Example usage:
pdf_path = '../PDFs/murder_on_delivery.pdf'
markdown_path = 'extracted_text.md'
extract_text_to_markdown(pdf_path, markdown_path)
