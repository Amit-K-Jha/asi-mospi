import os
import json
from crewai import Agent, Task, Crew, Process, LLM
from collections import OrderedDict

class EntityExtractor:
    def __init__(self):
        self.WATSONX_URL = os.getenv("WATSONX_URL")
        self.WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
        self.WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
        self.MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        self.llm = self._initialize_llm()

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
            base_url=self.WATSONX_URL,
            project_id=self.WATSONX_PROJECT_ID,
            api_key=self.WATSONX_APIKEY,
            parameters=parameters,
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

    def try_float(self,value):
        try:
            return float(value.replace(",", ""))
        except:
            return 0.0

    def sum_nested_values(self,freehold, leasehold):
        if isinstance(freehold, dict) and isinstance(leasehold, dict):
            result = {}
            for key in freehold:
                result[key] = self.sum_nested_values(freehold[key], leasehold.get(key, "0"))
            return result
        elif isinstance(freehold, str) and isinstance(leasehold, str):
            total = self.try_float(freehold) + self.try_float(leasehold)
            return f'{total:.2f}' if total != 0 else ""
        else:
            return ""

    def _create_agent(self):
        return Agent(
            role="Markdown-to-JSON Data Extractor",
            goal="Accurately extract financial values from a structured Markdown table and populate the corresponding fields in a predefined JSON format.",
            backstory=(
                "You are a financial data analyst specialized in translating tabular financial records into structured formats. "
                "You strictly follow instructions, avoid assumptions, and always maintain the integrity and structure of the original JSON. "
                "You never add extra fields or comments and return only the populated JSON."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )


    def _create_task(self, agent):
        return Task(

            description = (
                "You are provided with two inputs:\n"
                "- A JSON structure called `{json_input}` that includes asset categories such as 'Land', 'Plant & Building', 'Machinery', etc., each with nested key-value pairs like 'Gross Value (Rs.)', 'Depreciation', and 'Net Value'. Many of these fields are empty strings.\n"
                "- A Markdown-formatted table called `{markdown}` that contains actual financial data.\n\n"
                "Each asset category in the JSON has nested key-value pairs such as:\n"
                "- 'Gross Value (Rs.)' → 'Opening as on (3)', 'Addition during the year', etc.\n"
                "- 'Depreciation', 'Net Value', and other relevant subfields if applicable.\n\n"
                "Your task is to fill **only** the empty string fields in the input JSON using matching values from the Markdown content.\n\n"
                "Instructions:\n"
                "- Use **only** the Markdown data. Do not guess or generate values.\n"
                "- If multiple years are available, always use the most recent year (e.g., 2024 over 2023).\n"
                "- Match keys in the JSON exactly. Do not rename, reformat, or alter any structure.\n"
                "- If a matching value is not found in the Markdown, retain the field as an empty string. \n"
                "- For example, if the key 'Others' is not present in the Markdown data, leave its fields unchanged.\n"
                "- If the asset key in the JSON (e.g., 'Land') is not explicitly present in the Markdown table, do not attempt to infer values from related subcategories like 'Freehold Land' or 'Leasehold Land'. Leave the fields for 'Land' as empty strings in this case."
                "- However, if the JSON contains a specific key like 'Leasehold Land' and that exact category is present in the Markdown data, you may extract and fill the corresponding values."
                "- All populated values must be strings enclosed in double quotes.\n"
                "- Do NOT add comments, chain-of-thought reasoning, or formatting.\n"
                "- Output must be a single valid JSON object that strictly follows the **structure and order** of the input JSON.\n"
            ),
            expected_output="{json_input}",
            agent=agent,
        )

    def _run_agent(self, content:str,json_path:str,final_path:str,indexes:list):

        with open(json_path, "r", encoding="utf-8") as inf:
            json_to_fill = json.load(inf)


        block_data = json_to_fill["Type of Assets"]
        keys = list(block_data.keys())
        group_json = {}

        for group in indexes:
            group_dict = {}
            curr_keys = []
            for j in group:
                key = keys[j]
                group_dict[key] = block_data[key]
                curr_keys.append(key)

            json_input_str = json.dumps(group_dict, indent=2)

            extractor_agent = self._create_agent()
            extract_task = self._create_task(extractor_agent)
            crew = Crew(
                agents=[extractor_agent],
                tasks=[extract_task],
                verbose=True,
                process=Process.sequential,
            )

            result = crew.kickoff(inputs={"json_input": json_input_str, "markdown": content})
            filled_json_str = result.raw
            # print(filled_json_str)

            filled_json_str = (
                filled_json_str.replace("```", "")
                .replace("json", "")
                .strip()
            )

            try:
                filled_json = json.loads(filled_json_str)
                group_json.update(filled_json)
                print("✅ JSON parsed and added to group_json")
            except json.JSONDecodeError as e:
                print("❌ JSON decode error:", e)
                print("❗ Problematic string:", filled_json_str)



        # print("\n📦 All grouped JSONs:")
        # print(json.dumps(group_json, indent=2))
        # Ensure the directory exists
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        # Write to file
        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(group_json, f, indent=2)

        print(f"✅ JSON saved to: {final_path}")


if __name__ == "__main__":

    extractor = EntityExtractor()
    markdown_file_path ='/Users/kalpataruvijaydhakate/Desktop/MOSPI/recent_output.md' #"/Users/kalpataruvijaydhakate/Desktop/MOSPI/db_files_pdf/HIMALAYAWELLLNESS.md"
    json_path_block_c = "C:/Users/Chitransh/Downloads/IBM/ASI-MoSPI/app/Block_C.json"

    if not os.path.exists(markdown_file_path):
            raise FileNotFoundError(f"File not found: {markdown_file_path}")

    with open(markdown_file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

    if "Freehold Land" and "Leasehold Land" in markdown_content:
        print("True")
        json_path_land = "/Users/kalpataruvijaydhakate/Downloads/ASI-MoSPI/Land.json"
        indexes_land = [
            [0, 1]
            ]
        complete_land_json_path = extractor.get_final_output_path(markdown_file_path=markdown_file_path, json_file_path=json_path_land)
        extractor._run_agent(markdown_content,json_path_land, complete_land_json_path, indexes_land)
        with open(complete_land_json_path, "r", encoding="utf-8") as f:
            input_json_load = json.load(f)

        print(input_json_load)
        input_json_load = input_json_load
        freehold = input_json_load["Freehold Land"]
        leasehold = input_json_load["Leasehold Land"]
        land = extractor.sum_nested_values(freehold, leasehold)
        print(land)

        indexes_complete = [
            [1, 2],
            [3, 4, 5],
            [6, 8]
        ]

        complete_json_path_block_c = extractor.get_final_output_path(markdown_file_path=markdown_file_path, json_file_path=json_path_block_c)
        extractor._run_agent(markdown_content,json_path_block_c, complete_json_path_block_c, indexes_complete)
        with open(complete_json_path_block_c, "r", encoding="utf-8") as inf:
            original_dict = json.load(inf)

        completed_json_block_c = OrderedDict()
        completed_json_block_c['1. Land'] = land
        for key, value in original_dict.items():
            if key != '1. Land':
                completed_json_block_c[key] = value

        print(completed_json_block_c)
        with open(complete_json_path_block_c, "w", encoding="utf-8") as f:
            json.dump(completed_json_block_c, f, indent=2)


    else:

        indexes = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 8]
        ]
        complete_json_path_block_c = extractor.get_final_output_path(markdown_file_path=markdown_file_path, json_file_path=json_path_block_c)
        extractor._run_agent(markdown_content,json_path_block_c, complete_json_path_block_c, indexes)
        with open(complete_json_path_block_c, "r", encoding="utf-8") as inf:
            completed_json_block_c = json.load(inf)
            print(completed_json_block_c)
