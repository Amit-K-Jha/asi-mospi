import os
import json
from crewai import Agent, Task, Crew, Process, LLM

class G_BlockEntityExtractor:
    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()
        print("Watsonx credentials loaded for Block G")
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

    def _create_agent(self):
        return Agent(
            role="ASI Block G Financial Receipts Extractor",
            goal="Accurately extract Other Output / Receipts data from markdown financial statements and populate the Block G JSON strictly as per ASI rules.",
            backstory=(
            "You are a specialized ASI financial data extraction expert. "
            "You have deep knowledge of the ASI Instruction Manual, Annexure Tables, "
            "and ASI Schedule 2023–24. You understand that Block G captures ONLY "
            "explicitly reported receipts and that several items are ASI-derived "
            "and must NOT be calculated by the extractor. "
            "You extract values exactly as reported, without inference, calculation, "
            "unit conversion, or restructuring."
        ),
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
    )


    def _create_task(self, agent):
        return Task(
            description=(
            "You are given:\n"
            "- `{json_input}`: A JSON structure for Block G: OTHER OUTPUT/RECEIPTS where all "
            "'Receipts (Rs.)' fields are empty strings.\n"
            "- `{markdown}`: A markdown document containing audited balance sheet, "
            "profit & loss account, and notes.\n\n"

            "Your task is to populate ONLY those Block G fields whose values are "
            "EXPLICITLY and UNAMBIGUOUSLY available in the markdown.\n\n"

            "────────────────────────────\n"
            "CORE RULES (STRICT – SAME AS BLOCK D & F)\n"
            "────────────────────────────\n"
            "1. Use ONLY the markdown document as the data source.\n"
            "2. Fill ONLY empty string fields.\n"
            "3. DO NOT add, remove, rename, or restructure JSON keys.\n"
            "4. DO NOT calculate, derive, subtract, add, or infer any values.\n"
            "5. DO NOT normalize or convert units (lakhs/crores stay exactly as shown).\n"
            "6. Extract values EXACTLY as written (preserve commas, decimals, signs).\n"
            "7. If a value is not explicitly stated, leave the field as \"\".\n"
            "8. Return ONLY the final JSON. No explanations.\n\n"

            "────────────────────────────\n"
            "YEAR SELECTION\n"
            "────────────────────────────\n"
            "• If multiple years are present, ALWAYS use the most recent year "
            "(FY 2023–24 / 31-03-2024).\n\n"

            "────────────────────────────\n"
            "BLOCK G ITEM-WISE EXTRACTION LOGIC\n"
            "────────────────────────────\n"

            "1. Receipts from manufacturing services:\n"
            "   Extract ONLY if the markdown explicitly reports:\n"
            "   • Job work income\n"
            "   • Processing charges received\n"
            "   • Manufacturing services income\n"
            "   DO NOT use product sales or service revenue unless clearly labelled "
            "as job-work/processing.\n\n"

            "2. Receipts from non-manufacturing services:\n"
            "   Extract ONLY explicitly stated service income such as:\n"
            "   • Sales of services\n"
            "   • Transport / maintenance / design / consultancy services\n"
            "   DO NOT include sale of manufactured goods.\n\n"

            "3. Value of electricity generated and sold:\n"
            "   Extract ONLY if sale of electricity is explicitly reported.\n\n"

            "4. Value of own construction:\n"
            "   Extract ONLY if own construction / self-construction value is "
            "explicitly stated.\n\n"

            "5. Net balance of goods sold in same condition as purchased:\n"
            "   🚫 DO NOT COMPUTE.\n"
            "   Populate ONLY if the markdown explicitly provides this net figure.\n\n"

            "6. Rent received for plant & machinery and other fixed assets:\n"
            "   Extract ONLY if rent from machinery / equipment / assets is "
            "explicitly reported.\n\n"

            "7. Variation in stock of semi-finished goods:\n"
            "   🚫 DO NOT COMPUTE.\n"
            "   Populate ONLY if the markdown explicitly reports this value.\n\n"

            "8. Rent received for buildings:\n"
            "   Extract ONLY if building rent is explicitly stated.\n\n"

            "9. Rent / royalties on land, mines, quarries:\n"
            "   Extract ONLY if explicitly reported.\n\n"

            "10. Interest received:\n"
            "   Extract ONLY if interest income is reported as a distinct line item.\n"
            "   DO NOT split totals or aggregate sub-items.\n\n"

            "11. Sale value of goods sold in the same condition as purchased:\n"
            "   Extract ONLY gross sale value of traded goods or scrap sales.\n"
            "   DO NOT net against purchases.\n\n"

            "12. Other production subsidies:\n"
            "   Extract ONLY if production-linked subsidy is explicitly reported.\n\n"

            "────────────────────────────\n"
            "FORBIDDEN ACTIONS (CRITICAL)\n"
            "────────────────────────────\n"
            "• DO NOT compute Block G item 5 or 7.\n"
            "• DO NOT infer values from Block D or Block F.\n"
            "• DO NOT reclassify revenue lines.\n"
            "• DO NOT convert units.\n"
            "• DO NOT guess missing values.\n\n"

            "────────────────────────────\n"
            "OUTPUT REQUIREMENTS\n"
            "────────────────────────────\n"
            "• Output ONLY the populated JSON object.\n"
            "• No markdown, no explanations, no comments.\n"
        ),
            expected_output="{json_input}",
            agent=agent,
    )


    def _run_agent(self, content: str, json_path: str, final_path: str):
        """
        Runs the extraction agent to populate Block G JSON from markdown content.
        
        Args:
            content: Markdown content containing receipts data
            json_path: Path to the Block G JSON template
            final_path: Path where the populated JSON will be saved
        """
        # Load the JSON template
        with open(json_path, "r", encoding="utf-8") as inf:
            json_to_fill = json.load(inf)

        json_input_str = json.dumps(json_to_fill, indent=2)

        # Create agent and task
        extractor_agent = self._create_agent()
        extract_task = self._create_task(extractor_agent)
        
        # Create crew
        crew = Crew(
            agents=[extractor_agent],
            tasks=[extract_task],
            verbose=True,
            process=Process.sequential,
        )

        # Execute extraction
        print("\n" + "="*50)
        print("Starting Block G Extraction")
        print("="*50 + "\n")
        
        result = crew.kickoff(inputs={"json_input": json_input_str, "markdown": content})
        
        print("\n" + "="*50)
        print("Extraction Result:")
        print("="*50)
        print(result)

        # Clean the result
        filled_json_str = result.raw.replace("```", "").replace("json", "").strip()
        
        print("\n" + "="*50)
        print("Cleaned JSON String:")
        print("="*50)
        print(filled_json_str[:500] + "..." if len(filled_json_str) > 500 else filled_json_str)

        # Parse JSON
        try:
            filled_json = json.loads(filled_json_str)
            print("\n✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            print("\n❌ JSON decode error:", e)
            print("Problematic string:", filled_json_str)
            raise

        # Ensure output directory exists
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        # Save to file
        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(filled_json, f, indent=2)

        print(f"\n✅ Block G JSON saved to: {final_path}")
        
        return filled_json


if __name__ == "__main__":
    # Example usage
    extractor = G_BlockEntityExtractor()
    
    # Update these paths according to your setup
    markdown_file_path = "/path/to/your/ASI_Schedule_markdown.md"
    json_path_block_g = "/path/to/Block_G.json"
    
    # Check if markdown file exists
    if not os.path.exists(markdown_file_path):
        raise FileNotFoundError(f"Markdown file not found: {markdown_file_path}")
    
    # Read markdown content
    with open(markdown_file_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    
    # Generate output path
    final_path = extractor.get_final_output_path(
        markdown_file_path=markdown_file_path,
        json_file_path=json_path_block_g
    )
    
    print(f"Final output path: {final_path}")
    
    # Run extraction
    result = extractor._run_agent(markdown_content, json_path_block_g, final_path)
    
    # Display results
    print("\n" + "="*50)
    print("Final Populated Block G JSON:")
    print("="*50)
    print(json.dumps(result, indent=2))