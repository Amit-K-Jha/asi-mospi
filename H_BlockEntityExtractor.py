import os
import json
import re
from crewai import Agent, Task, Crew, Process, LLM

class H_BlockEntityExtractor:

    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        params = {
            "decoding_method": "sample",
            "max_new_tokens": 9000,
            "temperature": 0,
            "top_k": 10,
            "top_p": 1,
            "repetition_penalty": 0,
            "random_seed": 1,
        }
        return LLM(
            model=self.MODEL_ID,
            base_url=self.WATSONX_URL,
            project_id=self.WATSONX_PROJECT_ID,
            api_key=self.WATSONX_APIKEY,
            parameters=params,
        )

    # -------------------------
    # Agent / Task (C/D style)
    # -------------------------

    def _create_agent(self):
        return Agent(
            role="Block H Extractor",
            goal="Extract and fill Block H values from markdown using fuzzy matching.",
            backstory="Expert in ASI Schedule data mapping.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

    def _create_task(self, agent):
        return Task(
        description=(
            "You are a STRICT ASI Block H data extraction engine.\n\n"

            "BLOCK CONTEXT (MANDATORY TO FOLLOW):\n"
            "Block H: Indigenous input items consumed, as defined in ASI Schedule 2023–24 (Annexure-V, A-20).\n"
            "This block CANNOT be fully derived from Balance Sheets or P&L accounts.\n"
            "Balance Sheets generally contain ONLY AGGREGATED COST VALUES, not item-wise quantities.\n\n"

            "INPUTS PROVIDED:\n"
            "- json_input: Official Block H JSON structure (exact keys and serial numbers must be preserved).\n"
            "- markdown: Extracted text from Balance Sheet / P&L / Notes (SOLE source of truth).\n"
            "- annexure_synonyms: Reference keywords ONLY to locate relevant lines.\n\n"

            "ABSOLUTE RULES (NO EXCEPTIONS):\n"
            "1. Populate a field ONLY if an explicit numeric value is written in markdown.\n"
            "2. NEVER infer, calculate, derive, sum, subtract, average, or estimate any value.\n"
            "3. NEVER apply accounting logic, ASI logic, or business interpretation.\n"
            "4. NEVER compute totals (rows 12, 22, 23).\n"
            "5. If a value is not explicitly present, LEAVE THE FIELD AS AN EMPTY STRING.\n"
            "6. Use annexure_synonyms ONLY to FIND text — NEVER to infer values.\n"
            "7. Copy numeric values EXACTLY as written (no rounding, no unit conversion).\n"
            "8. Do NOT assume units (KWH, KG, TONNE, etc.) unless explicitly written.\n"
            "9. Do NOT add, remove, rename, or restructure any JSON keys.\n"
            "10. Output ONLY valid JSON. No explanations, no comments, no markdown.\n\n"

            "🚨 HARD CONSTRAINT — ROWS 1 TO 10 (CRITICAL):\n"
            "Rows 1 to 10 correspond to the 'Major ten basic items (indigenous)'.\n"
            "THESE ROWS MUST ALWAYS REMAIN COMPLETELY EMPTY.\n"
            "This is a STRICT, NON-NEGOTIABLE RULE.\n\n"
            "For rows 1 to 10:\n"
            "- DO NOT fill Item description\n"
            "- DO NOT fill Item code (NPC-MS)\n"
            "- DO NOT fill Unit of quantity\n"
            "- DO NOT fill Quantity consumed\n"
            "- DO NOT fill Purchase value (Rs.)\n"
            "- DO NOT fill Rate per unit (Rs.)\n"
            "- EVEN IF values appear to exist in markdown, IGNORE them.\n"
            "- EVEN IF annexure_synonyms match text, IGNORE them.\n"
            "- ALWAYS return rows 1–10 EXACTLY as empty strings.\n\n"

            "BLOCK-H-SPECIFIC RULES FOR OTHER ROWS:\n"
            "• Rows 11–21: You MAY fill ONLY 'Purchase value (Rs.)' if explicitly written.\n"
            "• Quantity and Rate fields MUST remain EMPTY unless BOTH quantity and unit are explicitly present.\n"
            "• Rows 12, 22, 23 (Totals): NEVER calculate; fill ONLY if explicitly printed in markdown.\n"
            "• Row 24 (Additional electricity requirement): ALWAYS leave EMPTY unless explicitly stated.\n\n"

            "AMBIGUITY HANDLING:\n"
            "- If multiple numbers appear near a keyword, choose ONLY the number clearly tied to that item.\n"
            "- If association is ambiguous, LEAVE THE FIELD EMPTY.\n\n"

            "FINAL OUTPUT REQUIREMENT:\n"
            "- Return ONLY the populated JSON.\n"
            "- Preserve json_input structure EXACTLY, including serial numbers (\"1.\" to \"24.\").\n"
        ),
        expected_output="{json_input}",
        agent=agent,
    )




    # -------------------------
    # Helper Functions
    # -------------------------

    def _clean_json(self, text):
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            cleaned = text[start:end]
        except:
            cleaned = text
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        return cleaned

    def _regex_extract(self, keywords, markdown):
        number_regex = r"(?:(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?)|\d+\.\d+)"
        for kw in keywords:
            for m in re.finditer(re.escape(kw), markdown, flags=re.IGNORECASE):
                start = max(0, m.start() - 80)
                end = min(len(markdown), m.end() + 80)
                snippet = markdown[start:end]
                num = re.search(number_regex, snippet)
                if num:
                    return num.group(0)
        return ""

    def _fill_missing(self, template_item, value):
        if not isinstance(template_item, dict):
            return template_item
        for k, v in template_item.items():
            if v == "" and value:
                template_item[k] = value
                break
        return template_item

    # -------------------------
    # MAIN METHOD COMPATIBLE WITH demo.py
    # -------------------------

    def _run_agent(self, content: str, json_path: str, final_path: str, batch_size: int = 5):

        with open(json_path, "r", encoding="utf-8") as f:
            base_json = json.load(f)

        block_data = base_json["Block H: Indigenous input items consumed"]
        keys = list(block_data.keys())

        # Create batches (just like C block)
        batches = [keys[i:i + batch_size] for i in range(0, len(keys), batch_size)]

        synonyms = {
        # DO NOT add synonyms for items 1–10 (must remain empty)

        "11.": ["Other basic items"],

        # Totals: ONLY if explicitly written as totals in notes (rare)
        "12.": ["Total cost of material consumed"],
    
        "13.": ["Non-basic chemicals"],

        "14.": ["Packing material"],

        # Electricity: value only, never quantity
        "15.": ["Electricity generated"],  # usually NOT present
        "16.": ["Electricity charges", "Electricity expense"],

        # Fuel: value only
        "17.": ["Petrol", "Diesel", "Fuel expenses", "Power & fuel"],
        "18.": ["Coal"],        # usually absent
        "19.": ["Gas"],         # usually absent
        "20.": ["Other fuel"],

        # Consumables
        "21.": ["Consumable stores", "Stores & spares"],

        # Totals — extremely strict
        "22.": ["Total power and fuel"],   # only if explicitly present
        "23.": ["Total cost of material consumed"],

        # Always empty
        "24.": []  # unmet electricity demand NEVER in balance sheet
    }


        agent = self._create_agent()
        task = self._create_task(agent)

        extracted = {}

        for batch_keys in batches:

            batch_json = {k: block_data[k] for k in batch_keys}
            json_str = json.dumps(batch_json, indent=2)

            syn = []
            for k in batch_keys:
                syn.extend(synonyms.get(k, []))

            crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=True,
                process=Process.sequential,
            )

            result = crew.kickoff(
                inputs={
                    "json_input": json_str,
                    "markdown": content,
                    "annexure_synonyms": ", ".join(syn),
                }
            )

            raw = getattr(result, "raw", str(result))
            cleaned = self._clean_json(raw)

            try:
                parsed = json.loads(cleaned)
                for key in parsed:
                    extracted[key] = parsed[key]
                continue
            
            except:
                for key in batch_keys:

                    row_no = int(key.replace(".", ""))

                    # -----------------------------
                    # HARD LOCK: ROWS 1–10
                    # -----------------------------
                    if row_no <= 10:
                        extracted[key] = block_data[key]
                        continue

                    # -----------------------------
                    # ROWS 11–24 (controlled fill)
                    # -----------------------------
                    extracted[key] = block_data[key].copy()

                    # Allow regex fallback ONLY for Purchase value (Rs.)
                    found = self._regex_extract(
                        synonyms.get(key, []),
                        content
                    )

                    if found:
                        extracted[key]["Purchase value (Rs.)"] = found


        final_output = {
            "Block H: Indigenous input items consumed": extracted
        }

        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2)

        # -----------------------------
        # FINAL ASI HARD GUARD
        # -----------------------------
        for key, row in extracted.items():
            row_no = int(key.replace(".", ""))

            # Rows 1–10: wipe everything
            if row_no <= 10:
                for field in row:
                    row[field] = ""
                continue

        # Rows 11–24: forbid auto-filled non-value fields
        for forbidden in [
            "Item description",
            "Unit of quantity",
            "Quantity consumed",
            "Rate per unit (Rs.)"
        ]:
            row[forbidden] = ""
        
        return final_output
