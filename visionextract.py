from pdf2image import convert_from_path
import base64
import requests
import os
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import time
import shutil

class PDFToMarkdownExtractor:
    def __init__(self, pdf_path, image_output_path):
        load_dotenv()
        self.pdf_path = pdf_path
        self.image_output_path = image_output_path
        self.WX_CREDENTIALS = {
            "url": "https://us-south.ml.cloud.ibm.com",
            "apikey": "o8l7Q4LcFCCyZpOrJAdxjhjpCEJgZXfjrmo9VINP2cnA" #os.getenv("WATSONX_APIKEY"),
        }
        self.api_url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"


        # Current prompt is generic
# New prompt should be:
        self.prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert at extracting Annual Survey of Industries (ASI) Schedule data from government forms.

<|start_header_id|>user<|end_header_id|>
You are analyzing an ASI Schedule 2023-24 form containing financial data in tabular format.

CRITICAL INSTRUCTIONS:
1. **Preserve Exact Values**: Extract numbers EXACTLY as shown - do not convert units
   - If value shows "10909000", write "10909000" (NOT "109.09" or "10.91 crores")
   - Maintain all decimal places exactly as printed
   
2. **Table Structure Recognition**:
   - Identify column headers precisely (e.g., "Opening as on 01/04/2023", "Closing as on 31/03/2024")
   - Map each value to its correct column
   - Preserve row labels exactly (e.g., "Land", "Building", "Plant and Machinery")
   
3. **Block Identification**:
   - Clearly mark which Block this is (Block A, B, C, D, E, F, G, H, I, J, K, L, M, N)
   - Include Block title in output
   
4. **Handle Complex Tables**:
   - For nested columns (e.g., "Gross Value (Rs.)" with sub-columns), preserve hierarchy
   - For calculated columns (e.g., "Closing = Opening + Addition - Deduction"), extract all components
   
5. **Blank vs Zero**:
   - If a cell is blank/empty, mark as "BLANK" or empty string
   - If a cell shows "0" or "0.00", preserve that exact value
   - Never assume or calculate missing values
   
6. **Data Validation**:
   - Cross-check that row totals match if "Total" or "Sub-total" rows exist
   - Flag any inconsistencies with [ALERT: mismatch]
   
7. **Output Format**:
   Return as structured Markdown with:
   - Block identifier (e.g., "## Block C: Fixed Assets")
   - Full table in Markdown format
   - Preserve all columns, all rows, all values exactly

Example Output Structure:
## Block C: Fixed Assets
| Sl No | Type of Asset | Opening Gross (Rs.) | Addition (Rs.) | ... |
|-------|--------------|-------------------|----------------|-----|
| 1 | Land | 10909000 | | ... |
| 2 | Building | 14874000 | 0 | ... |

NEVER:
- Convert to lakhs/crores
- Round numbers
- Skip blank cells
- Merge columns
- Summarize content
<|start_header_id|>assistant<|end_header_id|>
"""


    def pdf_to_images(self):
    # Delete the directory if it exists
        if os.path.exists(self.image_output_path):
            shutil.rmtree(self.image_output_path)

        # Recreate the directory
        os.makedirs(self.image_output_path)

        # Convert PDF to images and save them
        images = convert_from_path(
            self.pdf_path,
            poppler_path=r"C:\Users\Admin\OneDrive\Desktop\Applications\poppler-25.11.0\Library\bin",
        )
        for i, image in enumerate(images):
            image_path = os.path.join(self.image_output_path, f"page_{i + 1}.jpg")
            image.save(image_path)

    def sort_custom(self, param):
        try:
            val = int(param.split('_')[1].split('.')[0])
            return val
        except Exception:
            return float('inf')

    def image_encoding(self):
        encoded_images = []
        image_path_list = []
        for root, dirs, files in os.walk(self.image_output_path):
            for file in files:
                if file.endswith(".jpg") and file.startswith("page_"):
                    image_path_list.append(os.path.join(root, file))
        image_path_list.sort(key=self.sort_custom)
        for path in image_path_list:
            with open(path, 'rb') as image_file:
                encoded_bytes = base64.b64encode(image_file.read())
                encoded_str = encoded_bytes.decode('utf-8')
                encoded_images.append(encoded_str)
        return encoded_images

    def get_bearer_token(self):
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.WX_CREDENTIALS['apikey']}"
        response = requests.post(token_url, headers=headers, data=data)
        return response.json().get("access_token")

    def get_response(self, prompt, encoded_image, access_token):
        body = {
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}]}],
            "project_id": "41d71924-826e-4873-a7d3-5a16d198e6f6", #os.getenv("WATSONX_PROJECT_ID"),
            "model_id": "meta-llama/llama-4-maverick-17b-128e-instruct-fp8", #"meta-llama/llama-3-2-90b-vision-instruct",
            "decoding_method": "sample",
            "repetition_penalty": 1.0,
            "temperature": 0.1,  # Slight variation helps with complex structures
            "top_p": 0.95,       # More diversity in token selection
            "top_k": 50,         # Broader token consideration
            "max_tokens": 8000,  # Increase for longer tables
            "random_seed":1
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.post(self.api_url, headers=headers, json=body)
        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))
        return response.json()['choices'][0]['message']['content']

    def process_image(self, index, encoded_image, prompt, token):
        try:
            print(f"🔄 Processing image {index}")
            text = self.get_response(prompt, encoded_image, token)
            markdown = "\n" + ("===" * 20) + f" Page Number {index} " + ("===" * 20) + "\n"
            markdown += text
            return index, markdown
        except Exception as e:
            print(f"❌ Error processing image {index}: {e}")
            return index, ""

    def run(self):
        start_time = time.time()
        self.pdf_to_images()
        encoded_images = self.image_encoding()
        access_token = self.get_bearer_token()

        markdown_chunks = [None] * len(encoded_images)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.process_image, idx + 1, img, self.prompt, access_token): idx
                for idx, img in enumerate(encoded_images)
            }
            for future in as_completed(futures):
                index, result = future.result()
                markdown_chunks[index - 1] = result

        markdown_content = "\n".join(markdown_chunks)
        output_md_path = self.pdf_path.replace(".pdf", ".md")
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"✅ Markdown file saved to: {output_md_path}")
        print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")


    def validate_extraction(self, markdown_content):
        """
            Validate extracted content for common errors
        """
        validation_report = {
            'has_block_identifiers': False,
            'has_tables': False,
            'has_numeric_values': False,
            'potential_unit_conversion_errors': [],
            'blank_vs_zero_check': 'pass'
    }
    
        # Check for Block identifiers
        if any(f"Block {b}" in markdown_content for b in ['A','B','C','D','E','F','G','H','I','J']):
            validation_report['has_block_identifiers'] = True
    
        # Check for table markers
        if '|' in markdown_content and '---' in markdown_content:
            validation_report['has_tables'] = True
    
        # Check for unit conversion errors (common mistake)
        import re
        # Look for values that might have been converted to lakhs
        lakh_patterns = re.findall(r'\b\d{1,3}\.\d{2}\b(?!\d)', markdown_content)
        if len(lakh_patterns) > 20:  # Too many small decimals suggests conversion
            validation_report['potential_unit_conversion_errors'] = lakh_patterns[:5]
    
        # Check for numeric values
        if re.search(r'\d+', markdown_content):
            validation_report['has_numeric_values'] = True
    
        return validation_report        


# Example usage
if __name__ == "__main__":
    extractor = PDFToMarkdownExtractor(
        pdf_path=r"C:\Users\Chitransh\Downloads\ASI Schedule 2023-24.pdf",
        image_output_path="temp_uploaded_files/images"
    )
    extractor.run()