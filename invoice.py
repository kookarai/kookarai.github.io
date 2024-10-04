import fitz  # PyMuPDF
from openai import OpenAI

client = OpenAI(api_key="sk-SjyHZCZVAfahyXo8JxPvmDKsplW3Ji3KUtptpBuIifT3BlbkFJizrP3LjrVY8j8hJkpOi97cklqB1ATr5rV3x_TXNTUA")

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

def send_to_openai(extracted_text):
    prompt = f"Extract the relevant JSON data from the following text. please send me the json data for the whole pdf.:\n\n{extracted_text}"

    models = client.models.list()

    # Send the request to OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-2024-05-13",  # or any other model you're using
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the JSON data from the response
    json_data = response.choices[0].message.content
    return json_data


# Specify the path to the PDF
pdf_path = 'taco_186152685629642_merged.pdf'

# Extract the text
extracted_text = extract_text_from_pdf(pdf_path)
json = send_to_openai(extracted_text)

# Print the extracted text
print(json)
