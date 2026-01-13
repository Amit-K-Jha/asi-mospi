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
            role="Markdown-to-JSON Data Extractor",
            goal="Accurately extract financial values from a structured Markdown table and populate the corresponding fields in a predefined JSON format.",
            backstory=(
                "You are a data extraction bot. You do not calculate sums. "
                "Your only job is to find the value form the P&L statements in markdown conetent associated with a specific keywords . "
                "and return it in a structured JSON format."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )
 
    def _create_task(self, agent):
        # We pass the list of items to the LLM to look for
        all_keywords = self.bonus_keywords + self.pf_keywords
 
        description = (
            f"Analyze the provided Markdown content.\n"
            f"Search for the following line items in P&L statements of markdown content: {', '.join(all_keywords)}.\n"
            "**Instructions:**\n"
            "1. For each item found, extract the value from the **Current Year** column.\n"
            "2. If an item is NOT found, do not include it or set it to '0'.\n"
            "3. Do NOT attempt to sum the values. Just extract them.\n"
            "4. Return a valid JSON object where keys are the exact Item Names and values are the numbers (as strings).\n"
            "5. Remove commas from numbers (e.g. '1,500' -> '1500').\n\n"
            "**Markdown Content:**\n{content}\n\n"
            "**Expected JSON Output Format:**\n"
            "{ \"Bonus Paid\": \"10000\", \"Provident Fund\": \"500.50\", ... }"
        )
 
        return Task(
            description=description,
            expected_output='JSON object containing extracted values for found keys.',
            agent=agent
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
 
