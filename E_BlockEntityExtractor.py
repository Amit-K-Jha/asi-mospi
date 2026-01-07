import os
import json
from crewai import Agent, Task, Crew, Process, LLM
 
class E_BlockEntityExtractor:
    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()
 
        # Define keywords as class attributes so they can be accessed for summation
        self.bonus_keywords = [
            "Bonus Paid", "Ex Gratia Paid", "Festival Bonus", "Others (Bonus, etc.)",
            "Profit Sharing", "Target Achievement Scheme Expenditure (Yearly)", "Year-end Bonus"
        ]
 
        self.pf_keywords = [
                    "Provident Fund",
                    "PF Linked Insurance",
                    "ESIC",
                    "Gratuity",
                    "Group Insurance / Life Insurance",
                    "Work Injury Compensation",
                    "Superannuation / Pension",
                    "Labour Welfare",
                    "Retrenchment / Exit Compensation",
                    "Voluntary Retirement",
                    "Perquisites"
                ]
 
 
        # self.pf_keywords = [
        #     "Compensation for Work Injuries", "Contribution to PF/EPF/ESIC", "Contribution to Superannuation",
        #     "DLIF", "EDLIS", "Employee Group Insurance", "EPF/CPF", "ESI Contribution Expenses/Paid",
        #     "Fund Created for Work Injuries & Occupational Diseases", "Gratuity", "Group Gratuity Fund",
        #     "Group Insurance", "Labour Fund", "Labour Welfare Fund", "LIC Group Gratuity", "Old Age Benefits",
        #     "Others (PF, etc.)", "Pension Fund", "Perks / Perquisites", "PF & ESIC Expenses",
        #     "PF Linked Insurance", "Provident Fund", "Provident Fund Linked Insurance",
        #     "Retrenchment Compensation", "VRS", "Voluntary Retirement Scheme", "Welfare Fund Contribution"
        # ]
 
    def _initialize_llm(self):
        parameters = {
            "decoding_method": "sample",
            "max_new_tokens": 4000,
            "temperature": 0, # Keep temp 0 for extraction accuracy
            "top_k": 10,
            "top_p": 1,
            "repetition_penalty": 1.0,
            "random_seed": 1
        }
 
        return LLM(
            model=self.MODEL_ID,
            base_url=self.WATSONX_URL,
            project_id=self.WATSONX_PROJECT_ID,
            api_key=self.WATSONX_APIKEY,
            parameters=parameters,
        )
 
    def _create_agent(self):
        return Agent(
            role="ASI Block E Labour Cost Extractor",
            goal=(
            "Extract ONLY Block E Part B labour cost values (Items 11 and 12) "
            "from markdown content and populate the predefined JSON structure."
            ),
            backstory=(
            "You are a specialized ASI data extraction bot for Block E. "
            "You strictly follow ASI Schedule rules. "
            "You do NOT calculate, infer, aggregate, or estimate values. "
            "You ONLY copy exact values explicitly stated in the markdown. "
            "You NEVER populate fields outside the allowed scope."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )


    def _create_task(self, agent):

        description = (
            "You are given:\n"
            "- A JSON structure for **Block E: Employment & Labour Cost** with empty fields.\n"
            "- Markdown content extracted from Balance Sheet / Profit & Loss statements.\n\n"

        "YOUR TASK:\n"
        "Populate ONLY the following fields:\n"
        "• Block E → Part B → Item 11: Bonus (in Rs.)\n"
        "• Block E → Part B → Item 12: Contribution to provident & other funds (in Rs.)\n\n"

        "ABSOLUTE RULES (NON-NEGOTIABLE):\n"
        "1. You are STRICTLY ALLOWED to fill ONLY Item 11 and Item 12.\n"
        "2. ALL other fields in the JSON MUST remain EMPTY, even if values are visible.\n"
        "3. Extract values ONLY if they appear explicitly in the markdown.\n"
        "4. Copy values EXACTLY as written — do NOT remove commas, symbols, or decimals.\n"
        "5. DO NOT calculate totals, sums, or aggregates.\n"
        "6. DO NOT infer values from related fields.\n"
        "7. DO NOT add, rename, remove, or reorder any JSON keys.\n"
        "8. If a value is NOT found explicitly, LEAVE THE FIELD EMPTY.\n"
        "9. Return ONLY the final JSON — no explanation, no comments.\n\n"

        "ITEM DEFINITIONS:\n"
        "• Item 11 (Bonus): Include ONLY values explicitly labelled as "
        "Bonus / Ex-gratia / Festival Bonus / Year-end Bonus.\n"
        "• Item 12 (Provident & other funds): Include ONLY employer contributions "
        "such as PF / EPF / ESI / ESIC / Gratuity / Superannuation.\n\n"

        "INVALID SOURCES:\n"
        "• Derived totals\n"
        "• Wage or salary figures\n"
        "• Incentives or allowances\n"
        "• Employee deductions unless clearly marked as employer contribution\n\n"

        "MARKDOWN CONTENT:\n"
        "{content}\n\n"

        "OUTPUT REQUIREMENT:\n"
        "Return ONLY the completed JSON structure exactly matching the input schema."
    )

        return Task(
            description=description,
            expected_output="{json_input}",
            agent=agent,
        )
 
    def _safe_float(self, value):
        try:
            # Remove commas and spaces
            if isinstance(value, str):
                value = value.replace(",", "").replace(" ", "").strip()
            return float(value)
        except (ValueError, TypeError):
            return 0.0
 
    def _run_agent(self, content: str, json_path: str, final_path: str):
        # 1. Load the Blank Block E structure
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Block E JSON template not found at {json_path}")
 
        with open(json_path, "r", encoding="utf-8") as inf:
            block_e_data = json.load(inf)
 
        # 2. Run the Agent to extract individual values
        extractor_agent = self._create_agent()
        task = self._create_task(extractor_agent)
 
        crew = Crew(
            agents=[extractor_agent],
            tasks=[task],
            verbose=True,
            process=Process.sequential,
        )
 
        # Pass content explicitly
        result = crew.kickoff(inputs={"content": content})
 
        extracted_str = result.raw
        # Clean markdown code blocks if present
        if "```json" in extracted_str:
            extracted_str = extracted_str.split("```json")[1].split("```")[0]
        elif "```" in extracted_str:
            extracted_str = extracted_str.split("```")[1].split("```")[0]
 
        extracted_str = extracted_str.strip()
 
        # 3. Perform Summation in Python (Safe & Accurate)
        total_bonus = 0.0
        total_pf = 0.0
 
        try:
            extracted_data = json.loads(extracted_str)
            print("\n🔍 Raw Extracted Data from LLM:", extracted_data)
 
            # Calculate Bonus Total
            for key in self.bonus_keywords:
                # We check for exact match or simple partial match
                # (The LLM usually returns the exact key requested)
                val = extracted_data.get(key, 0)
                total_bonus += self._safe_float(val)
 
            # Calculate PF Total
            for key in self.pf_keywords:
                val = extracted_data.get(key, 0)
                total_pf += self._safe_float(val)
 
            bonus_val_str = f"{total_bonus:.2f}"
            pf_val_str = f"{total_pf:.2f}"
 
            print(f"🧮 Calculated Totals (Python) -> Bonus: {bonus_val_str}, PF: {pf_val_str}")
 
        except Exception as e:
            print(f"❌ Failed to parse extraction result or calculate sum: {e}")
            print(f"Raw Output: {extracted_str}")
            bonus_val_str = "0.00"
            pf_val_str = "0.00"
 
        # 4. Inject values into Block E structure
        try:
            category_staff = block_e_data.get("Category of staff", {})
 
            if "11. Bonus (in Rs.)" in category_staff:
                category_staff["11. Bonus (in Rs.)"]["Wages/ salaries (in Rs.) (8)"] = bonus_val_str
 
            if "12. Contribution to provident & other funds (in Rs.)" in category_staff:
                category_staff["12. Contribution to provident & other funds (in Rs.)"]["Wages/ salaries (in Rs.) (8)"] = pf_val_str
 
            block_e_data["Category of staff"] = category_staff
 
        except Exception as e:
            print(f"❌ Error updating Block E JSON structure: {e}")
 
        # 5. Save Final Output
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(block_e_data, f, indent=2)
 
        print(f"✅ Block E JSON saved to: {final_path}")
 