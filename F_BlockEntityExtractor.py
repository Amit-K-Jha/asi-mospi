import os
import json
from crewai import Agent, Task, Crew, Process, LLM

class F_BlockEntityExtractor:
    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()
        print("Watsonx credentials loaded")
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
            role="Financial Expense Data Extractor",
            goal="Accurately extract expense data from markdown documents and populate the Block F JSON structure for Other Expenses.",
            backstory=(
                "You are a specialized financial data analyst expert in extracting expense information "
                "from Annual Survey of Industries (ASI) documents. You understand the structure of Block F "
                "which captures various operational expenses like repair & maintenance, operating expenses, "
                "insurance, rent, R&D expenses, interest, and transportation costs. You strictly follow "
                "instructions, extract exact values without modifications, and maintain JSON structure integrity."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

    def _create_task(self, agent):
        return Task(
            description=(
            "You are provided with:\n"
            "1. `{json_input}`: A JSON structure for ASI Schedule Block F (OTHER EXPENSES) with empty string values.\n"
            "2. `{markdown}`: Extracted financial statements in markdown format (Balance Sheet, P&L, Notes).\n\n"

            "Your job is to populate ONLY the empty 'Expenditure (Rs.)' fields in the JSON strictly according to "
            "ASI Instruction Manual, Annexure Tables, and ASI Schedule rules.\n\n"

            "============================================================\n"
            "STEP 1: SOURCE HIERARCHY (MANDATORY)\n"
            "------------------------------------------------------------\n"
            "1. First check whether the markdown contains an explicit table titled:\n"
            "   'Block F: Other Expenses' (or equivalent ASI schedule table).\n"
            "2. IF SUCH A BLOCK F TABLE EXISTS:\n"
            "   - Extract values ONLY from that table.\n"
            "   - Copy values exactly as printed.\n"
            "   - Do NOT derive values from P&L or Notes.\n"
            "   - Skip all derivation rules.\n"
            "3. IF BLOCK F TABLE DOES NOT EXIST:\n"
            "   - Derive Block F using P&L and Notes strictly via Annexure mapping rules below.\n\n"

            "============================================================\n"
            "STEP 2: GENERAL EXTRACTION RULES\n"
            "------------------------------------------------------------\n"
            "- Use ONLY the most recent year (FY 2023-24).\n"
            "- Fill ONLY empty string fields.\n"
            "- Do NOT add, rename, delete, or reorder JSON keys.\n"
            "- Do NOT calculate totals, balances, or derived figures.\n"
            "- Do NOT combine unrelated expense heads.\n"
            "- If a value cannot be mapped with certainty, leave it as an empty string.\n\n"

            "============================================================\n"
            "STEP 3: ANNEXURE-BASED ITEM MAPPING RULES\n"
            "------------------------------------------------------------\n"

            "1. Work done by others on materials supplied:\n"
            "- Include ONLY job work / processing charges where material ownership remains with the unit.\n"
            "- Keywords: 'job work', 'processing charges', 'fabrication on supplied material'.\n"
            "- EXCLUDE services, outsourcing, transport, maintenance.\n\n"

            "2. Repair & Maintenance:\n"
            "(i) Buildings & construction:\n"
            "- Include ONLY structural / building / depot / office maintenance.\n"
            "- Keywords: building repair, depot maintenance, civil repair.\n"
            "(ii) Other fixed assets:\n"
            "- Include ONLY repair of plant, machinery, vehicles, computers, equipment.\n"
            "- Keywords: repair, servicing, overhaul.\n"
            "- EXCLUDE running costs, fuel, operations, usage charges.\n\n"

            "3. Operating expenses:\n"
            "- Include routine administrative and compliance overheads ONLY.\n"
            "- Examples: accounting, legal fees, office expenses, printing, subscriptions, telephone.\n"
            "- EXCLUDE repairs, fuel, rent, insurance, transport, interest, depreciation, employee cost.\n\n"

            "4. Raw materials for own construction:\n"
            "- Include ONLY materials explicitly consumed for own construction / capital work.\n"
            "- If not explicitly stated, leave blank.\n\n"

            "5. Insurance charges:\n"
            "- Include insurance premiums only.\n"
            "- EXCLUDE GST reversals, penalties, or provisions.\n\n"

            "6. Rent paid for plant & machinery:\n"
            "- Include ONLY machinery or equipment lease rent.\n"
            "- Generic 'Rent' must NOT be mapped here.\n\n"

            "7. R&D expenses:\n"
            "- Include ONLY explicitly stated R&D expenditure.\n"
            "- If absent, leave blank.\n\n"

            "8. Rent paid for buildings:\n"
            "- Include building / office / depot rent.\n"
            "- If rent is generic and not split, map it here.\n\n"

            "9. Rent for land / royalty:\n"
            "- Include ONLY land lease rent or mining royalties.\n\n"

            "10. Interest paid:\n"
            "- Include ONLY interest component from finance costs.\n"
            "- EXCLUDE loan processing fees, bank charges, penalties.\n\n"

            "11. Purchase value of goods sold as purchased:\n"
            "- Include purchase value of traded goods sold without processing.\n"
            "- EXCLUDE manufactured goods.\n\n"

            "12. Inward transportation cost:\n"
            "- Include freight or cartage inward ONLY.\n\n"

            "13. Outward transportation cost:\n"
            "- Include delivery, freight outward, distribution transport ONLY.\n\n"

            "============================================================\n"
            "STEP 4: OUTPUT RULES (STRICT)\n"
            "------------------------------------------------------------\n"
            "- Output ONLY the final JSON object.\n"
            "- No explanations, no comments, no markdown formatting.\n"
            "- Preserve numeric values exactly as printed.\n"
            "- Leave fields empty if not explicitly identifiable.\n"
        ),
        expected_output="{json_input}",
        agent=agent,
    )


    def _run_agent(self, content: str, json_path: str, final_path: str):
        """
        Runs the extraction agent to populate Block F JSON from markdown content.
        
        Args:
            content: Markdown content containing expense data
            json_path: Path to the Block F JSON template
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
        print("Starting Block F Extraction")
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

        print(f"\n✅ Block F JSON saved to: {final_path}")
        
        return filled_json


if __name__ == "__main__":
    # Example usage
    extractor = F_BlockEntityExtractor()
    
    # Update these paths according to your setup
    markdown_file_path = "/path/to/your/ASI_Schedule_markdown.md"
    json_path_block_f = "/path/to/Block_F.json"
    
    # Check if markdown file exists
    if not os.path.exists(markdown_file_path):
        raise FileNotFoundError(f"Markdown file not found: {markdown_file_path}")
    
    # Read markdown content
    with open(markdown_file_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    
    # Generate output path
    final_path = extractor.get_final_output_path(
        markdown_file_path=markdown_file_path,
        json_file_path=json_path_block_f
    )
    
    print(f"Final output path: {final_path}")
    
    # Run extraction
    result = extractor._run_agent(markdown_content, json_path_block_f, final_path)
    
    # Display results
    print("\n" + "="*50)
    print("Final Populated Block F JSON:")
    print("="*50)
    print(json.dumps(result, indent=2))