import fitz  # PyMuPDF


# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Initialize an empty string to hold the extracted text
    extracted_text = ""

    # Iterate over the pages in the PDF
    for page_num in range(len(pdf_document)):
        # Get the page
        page = pdf_document.load_page(page_num)

        # Extract the text from the page
        text = page.get_text("text")

        # Append the extracted text
        extracted_text += f"Page {page_num + 1}:\n{text}\n"

    # Close the PDF file
    pdf_document.close()

    return extracted_text


# Specify the path to the PDF
pdf_path = 'invoice2.pdf'

# Extract the text
extracted_text = extract_text_from_pdf(pdf_path)

# Print the extracted text
print(extracted_text)
