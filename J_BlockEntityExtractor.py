import os
import json
from crewai import Agent, Task, Crew, Process, LLM

class J_BlockEntityExtractor:
    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()
        print("Watsonx credentials initialized")
        print(f"API Key: {self.WATSONX_APIKEY[:10]}..." if self.WATSONX_APIKEY else "No API Key")
        print(f"Project ID: {self.WATSONX_PROJECT_ID}")

    def _initialize_llm(self):
        parameters = {
            "decoding_method": "sample",
            "max_new_tokens": 12000,
            "temperature": 0,
            "top_k": 10,
            "top_p": 1,
            "repetition_penalty": 0,
            "random_seed": 1
        }

        return LLM(
            model=self.MODEL_ID,
            base_url=self.WATSONX_URL,
            project_id=self.WATSONX_PROJECT_ID,
            api_key=self.WATSONX_APIKEY,
            parameters=parameters
        )

    def _create_agent(self):
        return Agent(
            role="Products and By-products Data Extractor",
            goal="Accurately extract product manufacturing and sales data from markdown tables and populate the corresponding fields in a predefined JSON format for Block J.",
            backstory=(
                "You are a manufacturing data analyst specialized in extracting product-level information "
                "including quantities manufactured, quantities sold, sales values, taxes, and distributive expenses. "
                "You understand revenue recognition, tax structures (GST, Excise Duty, VAT), and how to calculate "
                "per-unit net sale values and ex-factory values. You strictly follow instructions, avoid assumptions, "
                "and maintain the integrity of the original JSON structure without adding extra fields or comments."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

    def _create_task(self, agent):
        return Task(
            description=(
                "You are provided with two inputs:\n"
                "- A JSON structure called `{json_input}` that includes product/by-product entries with fields like:\n"
                "  * 'Item description'\n"
                "  * 'Item code (NPCMS)'\n"
                "  * 'Unit of quantity'\n"
                "  * 'Quantity manufactured'\n"
                "  * 'Quantity sold'\n"
                "  * 'Gross sale value (Rs.)'\n"
                "  * 'Distributive expenses' (GST, Excise Duty/Sales Tax/VAT, Other Distributive Expenses, Subsidy)\n"
                "  * 'Per unit net sale value (Rs.)'\n"
                "  * 'Ex-factory value of quantity manufactured (Rs.)'\n"
                "- A Markdown-formatted table called `{markdown}` that contains actual product manufacturing and sales data.\n\n"
                
                "Your task is to fill **only** the empty string fields in the input JSON using matching values from the Markdown content.\n\n"
                
                "CRITICAL JSON FORMATTING RULES:\n"
                "1. Output MUST be valid, parseable JSON\n"
                "2. ALL string values MUST be properly escaped\n"
                "3. NO line breaks within string values\n"
                "4. Replace any newlines in extracted text with spaces\n"
                "5. Escape special characters: quotes (\"), backslashes (\\), etc.\n"
                "6. Keep string values concise - if product name is very long, truncate to 100 characters\n"
                "7. Do NOT include explanations, comments, or markdown formatting\n"
                "8. Output ONLY the JSON object, nothing else\n\n"
                
                "Instructions:\n"
                "1. **Data Source**: Use **only** the Markdown data. Do not guess or generate values.\n"
                "2. **Product Identification**: \n"
                "   - Match products by their description in the markdown table\n"
                "   - Look for product names under columns like 'Products/By-products description' or similar\n"
                "   - The JSON contains up to 10 major items (1-10) plus 'Other products/by-products' (11) and 'Total' (12)\n"
                "3. **Field Matching Rules**:\n"
                "   - 'Item description': Extract product name, clean any special characters, max 100 chars\n"
                "   - 'Item code (NPCMS)': Extract the NPCMS code if present, otherwise leave empty\n"
                "   - 'Unit of quantity': Extract unit (e.g., 'Kg', 'Tonne', 'Litre', 'Number', 'Metre')\n"
                "   - 'Quantity manufactured': Extract numeric value as string (e.g., \"1000\")\n"
                "   - 'Quantity sold': Extract numeric value as string\n"
                "   - 'Gross sale value (Rs.)': Extract numeric value as string\n"
                "   - 'Goods and Services Tax(GST)': Extract GST amount\n"
                "   - 'Excise Duty/Sales Tax/VAT/Other Taxes, if any': Extract tax amounts\n"
                "   - 'Other Distributive Expenses': Extract distribution expenses\n"
                "   - 'Subsidy (-)': Extract subsidy amount\n"
                "   - 'Per unit net sale value (Rs.)': Calculate or extract as string with 2 decimals\n"
                "   - 'Ex-factory value of quantity manufactured (Rs.)': Calculate or extract as string\n"
                "4. **Special Items**:\n"
                "   - Item 11 'Other products/by-products': Aggregates products not in items 1-10\n"
                "   - Item 12 'Total': Sum of all items (1-11)\n"
                "   - Item 13 'Share (%) of products/by-products directly exported': Extract export percentage\n"
                "5. **String Safety**:\n"
                "   - Replace any quotes in product names with apostrophes\n"
                "   - Remove or replace newline characters\n"
                "   - Keep descriptions under 100 characters\n"
                "   - Use empty string \"\" for missing data\n"
                "6. **Missing Data Handling**:\n"
                "   - If a product exists in JSON but not in markdown, leave all its fields as empty strings\n"
                "   - If a field cannot be found or calculated, retain it as an empty string\n"
                "   - Do not infer or estimate missing values\n"
                "7. **Output Requirements**:\n"
                "   - Output ONLY valid JSON, nothing else\n"
                "   - NO markdown code fences (no ```json or ```)\n"
                "   - NO explanations before or after the JSON\n"
                "   - NO comments within the JSON\n"
                "   - Ensure all quotes and braces are properly matched\n"
            ),
            expected_output="{json_input}",
            agent=agent,
        )

    def _clean_json_string(self, json_str):
        """Clean and fix common JSON formatting issues"""
        # Remove markdown code blocks
        json_str = json_str.replace("```json", "").replace("```", "").strip()
        
        # Remove any text before the first {
        start_idx = json_str.find("{")
        if start_idx > 0:
            json_str = json_str[start_idx:]
        
        # Remove any text after the last }
        end_idx = json_str.rfind("}")
        if end_idx > 0:
            json_str = json_str[:end_idx + 1]
        
        return json_str

    def _run_agent(self, content: str, json_path: str, final_path: str):
        with open(json_path, "r", encoding="utf-8") as inf:
            json_to_fill = json.load(inf)

        json_input_str = json.dumps(json_to_fill, indent=2)

        extractor_agent = self._create_agent()
        extract_task = self._create_task(extractor_agent)
        crew = Crew(
            agents=[extractor_agent],
            tasks=[extract_task],
            verbose=True,
            process=Process.sequential,
        )

        result = crew.kickoff(inputs={"json_input": json_input_str, "markdown": content})
        print("Result for Block J: ", result)

        filled_json_str = self._clean_json_string(result.raw)
        print("Final Block J json (first 500 chars):\n")
        print(filled_json_str[:500])

        try:
            filled_json = json.loads(filled_json_str)
            print("✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
            print("Problematic section:", filled_json_str[max(0, e.pos-100):min(len(filled_json_str), e.pos+100)])
            
            # Try to save what we have and create a minimal valid JSON
            print("⚠️ Attempting to return blank template due to parsing error")
            filled_json = json_to_fill
            
            # Save the problematic output for debugging
            error_path = final_path.replace(".json", "_error.txt")
            with open(error_path, "w", encoding="utf-8") as f:
                f.write(filled_json_str)
            print(f"⚠️ Problematic output saved to: {error_path}")

        print("final_path: ", final_path)

        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(filled_json, f, indent=2)

        print(f"✅ JSON saved to: {final_path}")

    def get_final_output_path(self, markdown_file_path, json_file_path):
        """
        Given paths to a Markdown file and a JSON file, returns the final output path
        in the format: <markdown_filename>-<json_filename>.json
        """
        directory = os.path.dirname(markdown_file_path)
        markdown_filename = os.path.splitext(os.path.basename(markdown_file_path))[0].strip()
        json_basename = os.path.splitext(os.path.basename(json_file_path))[0].strip()

        final_path = os.path.join(directory, f"{markdown_filename}-{json_basename}.json")
        return final_path


# Example usage
if __name__ == "__main__":
    extractor = J_BlockEntityExtractor()
    
    # Example paths - modify as needed
    markdown_file_path = "/path/to/your/balance_sheet.md"
    json_path = "/path/to/Block_J.json"
    
    if not os.path.exists(markdown_file_path):
        raise FileNotFoundError(f"File not found: {markdown_file_path}")

    with open(markdown_file_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    final_path = extractor.get_final_output_path(markdown_file_path, json_path)
    print("Final path:", final_path)
    
    extractor._run_agent(markdown_content, json_path, final_path)