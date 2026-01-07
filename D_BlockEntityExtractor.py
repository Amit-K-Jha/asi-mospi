

import os
import json
from crewai import Agent, Task, Crew, Process, LLM

class D_BlockEntityExtractor:
    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()
        print("Watsonx creds")
        print(self.WATSONX_APIKEY,self.WATSONX_PROJECT_ID)
    def _initialize_llm(self):
        parameters = {
            "decoding_method": "sample",
            "max_new_tokens": 12000,
            "temperature": 0,
            "top_k": 10,
            "top_p": 1,
            "repetition_penalty": 0,
            "random_seed" : 1
        }

        return LLM(
            model=self.MODEL_ID,
            #provider="ibm",
            base_url=self.WATSONX_URL,
            project_id=self.WATSONX_PROJECT_ID,
            api_key=self.WATSONX_APIKEY,
            parameters=parameters
        )

    def _create_agent(self):
        return Agent(
            role="User Data Completer",
            goal="Fill in missing values in a JSON structure accurately using provided knowledge sources.",
            backstory="You are an expert at understanding structured data and enriching missing values by carefully matching keys and extracting precise values from available context.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

    def _create_task(self, agent):
        return Task(
            description=(
            "You are an ASI-compliant financial data extractor.\n\n"

            "INPUTS PROVIDED:\n"
            "- {json_input}: A JSON object representing **ASI Schedule Block D – Working Capital and Loans**, "
            "  where some fields contain empty string values.\n"
            "- {markdown}: A markdown document containing an audited Balance Sheet and Notes, "
            "  with values reported for **As at March 31, 2023 (Opening)** and **As at March 31, 2024 (Closing)**.\n\n"

            "OBJECTIVE:\n"
            "Fill **ONLY the empty fields** in the JSON using the markdown document, "
            "strictly following ASI Schedule Block D rules. "
            "Do NOT modify any non-empty field.\n\n"

            "GLOBAL RULES (MANDATORY):\n"
            "1. Use the markdown document as the **SOLE source of truth**.\n"
            "2. Extract values ONLY if they are **explicitly present** in the markdown.\n"
            "3. If a value cannot be found clearly, leave the field as an empty string.\n"
            "4. NEVER invent, infer, estimate, or rebalance values.\n"
            "5. Preserve numbers **exactly as written** (including commas and decimals).\n"
            "6. Correctly interpret numeric formats:\n"
            "   - Comma (,) is a thousands separator\n"
            "   - Dot (.) is a decimal separator\n"
            "7. DO NOT output explanations, reasoning, or chain-of-thought.\n"
            "8. Output ONLY the final updated JSON with the same structure as input.\n\n"

            "OPENING vs CLOSING LOGIC (CRITICAL):\n"
            "- Fields labeled **Opening (Rs.)** MUST use values from:\n"
            "  → 'As at March 31, 2023'\n"
            "- Fields labeled **Closing (Rs.)** MUST use values from:\n"
            "  → 'As at March 31, 2024'\n\n"

            "BLOCK D FIELD-SPECIFIC EXTRACTION RULES:\n\n"

            "ITEM (1): Raw Materials & Components and Packing Materials\n"
            "- Search inventory notes/table for:\n"
            "  • 'Raw materials'\n"
            "  • 'Packing materials'\n"
            "  • OR 'Raw materials (including packing materials)'\n"
            "- Apply the following logic:\n"
            "  a) If only a combined value exists → use it directly.\n"
            "  b) If raw and packing are separate:\n"
            "     - Raw Materials = value under 'Raw materials'\n"
            "     - Packing Materials = value under 'Packing materials'\n"
            "     - Raw + Packing = sum of both\n"
            "- Apply separately for Opening (2023) and Closing (2024).\n\n"

            "ITEMS (2) & (3): Fuels & Lubricants, Spares / Stores / Others\n"
            "- Extract ONLY if explicitly listed in inventory notes.\n"
            "- If not listed separately, leave as empty.\n\n"

            "ITEMS (4), (7), (11), (15), (16): DERIVED FIELDS\n"
            "- DO NOT manually calculate or override these.\n"
            "- Fill them ONLY IF the markdown explicitly provides the totals.\n"
            "- Otherwise, leave them empty.\n\n"

            "ITEMS (5) & (6): WIP and Finished Goods\n"
            "- Extract from inventory notes ONLY if shown separately.\n"
            "- If not available, leave empty.\n\n"

            "ITEM (8): Cash in Hand & at Bank\n"
            "- Extract from Balance Sheet or Notes under:\n"
            "  • 'Cash and cash equivalents'\n"
            "  • 'Cash & Bank balances'\n"
            "- If the markdown shows subtotals (e.g., Sub-total I + Sub-total II), "
            "  use the FINAL TOTAL ONLY.\n\n"

            "ITEM (9): Sundry Debtors\n"
            "- Extract from:\n"
            "  • 'Trade receivables'\n"
            "  • 'Sundry debtors'\n"
            "- Use gross value (do not net provisions unless markdown already nets it).\n\n"

            "ITEM (10): Other Current Assets\n"
            "- Extract from:\n"
            "  • 'Other current assets'\n"
            "  • 'Loans & advances (current)'\n"
            "- Do NOT include inventories or cash here.\n\n"

            "ITEM (12): Sundry Creditors\n"
            "- Extract from:\n"
            "  • 'Trade payables'\n"
            "  • 'Sundry creditors'\n\n"

            "ITEM (13): Overdraft / Cash Credit / Short-term Loans\n"
            "- Extract from:\n"
            "  • 'Short-term borrowings'\n"
            "  • 'Cash credit'\n"
            "  • 'Overdraft'\n\n"

            "ITEM (14): Other Current Liabilities\n"
            "- Extract ONLY if explicitly listed.\n"
            "- If not separately disclosed, leave empty.\n\n"

            "ITEM (17): Outstanding Loans (excluding interest but including deposits)\n"
            "- Extract from:\n"
            "  • 'Long-term borrowings'\n"
            "  • 'Outstanding loans'\n"
            "- Exclude interest components unless explicitly included in the value.\n\n"

            "FINAL OUTPUT RULES:\n"
            "- Return ONLY the completed JSON.\n"
            "- Preserve original key names and structure.\n"
            "- Do NOT add, remove, or rename fields.\n"
        ),
        expected_output="{json_input}",
        agent=agent,
    )


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
        print("Result for Block D: ", result)

        filled_json_str = result.raw.replace("```", "").replace("json", "")
        print("Final Block D json\n")
        print(filled_json_str)

        try:
            filled_json = json.loads(filled_json_str)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            print("Problematic string:", filled_json_str)
            raise

        print("final_path: ",final_path)
        # full_file_path = os.path.join(final_path, "output_Block_D.json")



        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(filled_json, f, indent=2)

        print(f"\u2705 JSON saved to: {final_path}")

# if __name__ == "__main__":

#     extractor = D_BlockEntityExtractor()
#     markdown_file_path = "/Users/kalpataruvijaydhakate/Desktop/MOSPI/db_files_pdf/SKH BALANCE SHEET.md"
#     if not os.path.exists(markdown_file_path):
#             raise FileNotFoundError(f"File not found: {markdown_file_path}")

#     with open(markdown_file_path, "r", encoding="utf-8") as f:
#             markdown_content = f.read()


#     json_path = "/Users/kalpataruvijaydhakate/Desktop/MOSPI/Block_D.json"
#     directory = os.path.dirname(markdown_file_path)
#     markdown_filename = os.path.splitext(os.path.basename(markdown_file_path))[0].strip()

#     # Extract base name of JSON file (without extension)
#     json_basename = os.path.splitext(os.path.basename(json_path))[0]

#     # Create final output path
#     final_path = os.path.join(directory, f"{markdown_filename}-{json_basename}.json")

#     print("Final path:", final_path)
#     extractor._run_agent(markdown_content,json_path, final_path)

