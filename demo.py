from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
import shutil
import os
import json
from collections import OrderedDict
import traceback

from D_BlockEntityExtractor import D_BlockEntityExtractor
from E_BlockEntityExtractor import E_BlockEntityExtractor
from C_BlockEntityExtractor import EntityExtractor
from F_BlockEntityExtractor import F_BlockEntityExtractor
from G_BlockEntityExtractor import G_BlockEntityExtractor
from H_BlockEntityExtractor import H_BlockEntityExtractor
from J_BlockEntityExtractor import J_BlockEntityExtractor
from AssestJsonProcessor import AssetJsonProcessor
from G_Block_Calculations import BlockGJsonProcessor
from H_Block_Calculations import BlockHJsonProcessor
from J_Block_Calculations import BlockJJsonProcessor
from visionextract import PDFToMarkdownExtractor
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust based on frontend host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_dir = "tmp/mospi_uploads"


@app.post("/process")
async def process_pdf(pdf: UploadFile = File(...)):
    try:
        # Prepare upload directory
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        os.makedirs(upload_dir)

        # Save PDF
        temp_pdf_path = os.path.join(upload_dir, pdf.filename)
        with open(temp_pdf_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)

        # Set paths
        markdown_path = temp_pdf_path.replace(".pdf", ".md")
        image_output_path = os.path.join(upload_dir, "images")
        output_dir = os.path.join(upload_dir, "Outputs")
        os.makedirs(output_dir, exist_ok=True)

        block_a_json_path = "Block_A.json"
        block_b_json_path = "Block_B.json"
        block_c_json_path = "Block_C.json"
        block_d_json_path = "Block_D.json"
        block_e_json_path = "Block_E.json"
        block_f_json_path = "Block_F.json"
        block_g_json_path = "Block_G.json"
        block_h_json_path = "Block_H.json"
        block_i_json_path = "Block_I.json"
        block_j_json_path = "Block_J.json"
        block_k_json_path = "Block_K.json"
        block_l_json_path = "Block_L.json"
        block_m_json_path = "Block_M.json"
        block_n_json_path = "Block_N.json"
        

        # Verify required files exist
        for path in [block_a_json_path, block_b_json_path, block_c_json_path, block_d_json_path, block_e_json_path, block_f_json_path, block_g_json_path, block_h_json_path, block_i_json_path, block_j_json_path, block_k_json_path, block_l_json_path, block_m_json_path, block_n_json_path]:
            if not os.path.exists(path):
                return JSONResponse(status_code=400, content={"error": f"Missing required file: {path}"})

        # Convert PDF to Markdown
        extractor = PDFToMarkdownExtractor(temp_pdf_path, image_output_path)
        extractor.run()

        with open(markdown_path, "r", encoding="utf-8") as md_file:
            markdown_content = md_file.read()

        # Initialize processors
        block_c_processor = EntityExtractor()
        block_d_processor = D_BlockEntityExtractor()
        block_e_processor = E_BlockEntityExtractor()
        block_f_processor = F_BlockEntityExtractor()
        block_g_processor = G_BlockEntityExtractor()
        block_h_processor = H_BlockEntityExtractor()
        block_j_processor = J_BlockEntityExtractor()

        # --- BLOCK A PROCESSING ---
        block_a_json_path = "Block_A.json"

        with open(block_a_json_path, "r", encoding="utf-8") as f_a:
            block_a_json = json.load(f_a)

        block_a_dict = block_a_json.get("Block A: Identification particulars (for official use)", {})

        df_a = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_a_dict.items()]
        )

        # --- BLOCK B PROCESSING ---
        block_b_json_path = "Block_B.json"

        with open(block_b_json_path, "r", encoding="utf-8") as f_b:
            block_b_json = json.load(f_b)

        block_b_dict = block_b_json.get("Block B: Particulars of the factory", {})

        df_b = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_b_dict.items()]
        )
        
        # --- Block C Processing ---
        try:
            if "Freehold Land" and "Leasehold Land" in markdown_content:
                json_path_land = "Land.json"
                indexes_land = [[0, 1]]
                complete_land_json_path = block_c_processor.get_final_output_path(
                    markdown_file_path=markdown_path, json_file_path=json_path_land)
                block_c_processor._run_agent(markdown_content, json_path_land, complete_land_json_path, indexes_land)

                with open(complete_land_json_path, "r", encoding="utf-8") as f:
                    input_json_load = json.load(f)

                freehold = input_json_load.get("Freehold Land", {})
                leasehold = input_json_load.get("Leasehold Land", {})
                land = block_c_processor.sum_nested_values(freehold, leasehold)

                indexes_complete = [[1, 2], [3, 4, 5], [6, 8]]
                complete_json_path_block_c = os.path.join(output_dir, "output_Block_C.json")
                block_c_processor._run_agent(markdown_content, block_c_json_path, complete_json_path_block_c, indexes_complete)

                with open(complete_json_path_block_c, "r", encoding="utf-8") as inf:
                    original_dict = json.load(inf)

                completed_json_block_c = OrderedDict()
                completed_json_block_c['1. Land'] = land
                for key, value in original_dict.items():
                    if key != '1. Land':
                        completed_json_block_c[key] = value

                with open(complete_json_path_block_c, "w", encoding="utf-8") as f:
                    json.dump(completed_json_block_c, f, indent=2)

            else:
                indexes = [[0, 1, 2], [3, 4, 5], [6, 8]]
                complete_json_path_block_c = os.path.join(output_dir, "output_Block_C.json")
                block_c_processor._run_agent(markdown_content, block_c_json_path, complete_json_path_block_c, indexes)

                with open(complete_json_path_block_c, "r", encoding="utf-8") as inf:
                    completed_json_block_c = json.load(inf)

            with open(block_c_json_path, "r", encoding="utf-8") as f:
                blank_json_block_c = json.load(f)

            processor = AssetJsonProcessor(
                filled_json=completed_json_block_c,
                blank_json=blank_json_block_c
            )
            final_block_c_result = processor.fill_blank_json()

            with open(complete_json_path_block_c, "w", encoding="utf-8") as f:
                json.dump(final_block_c_result, f, indent=2)

        except Exception:
            traceback.print_exc()
            complete_json_path_block_c = None

        # --- Block D Processing ---
        try:
            block_d_output = os.path.join(output_dir, "output_Block_D.json")

            # Fix: Ensure directory creation doesn't break
            output_dirname = os.path.dirname(block_d_output)
            print("Demo output_dirname: ",output_dirname)
            
            if output_dirname:
                os.makedirs(output_dirname, exist_ok=True)

            block_d_processor._run_agent(markdown_content, block_d_json_path, block_d_output)

        except Exception:
            traceback.print_exc()
            block_d_output = None

        # --- Block E Processing ---
        try:
            block_e_output = os.path.join(output_dir, "output_Block_E.json")

            output_dirname = os.path.dirname(block_e_output)
            if output_dirname:
                os.makedirs(output_dirname, exist_ok=True)

            # STRICT extraction: ONLY Part B → Items 11 & 12
            block_e_processor._run_agent(
                content=markdown_content,
                json_path=block_e_json_path,
                final_path=block_e_output
            )

            print(f"✅ Block E extraction completed (Items 11 & 12 only): {block_e_output}")

        except Exception:
            traceback.print_exc()
            block_e_output = None    

        # --- Block F Processing ---
        try:
            block_f_output = os.path.join(output_dir, "output_Block_F.json")

            # Ensure directory exists
            output_dirname = os.path.dirname(block_f_output)
            if output_dirname:
                os.makedirs(output_dirname, exist_ok=True)

            block_f_processor._run_agent(markdown_content, block_f_json_path, block_f_output)
            print(f"✅ Block F processing completed: {block_f_output}")

        except Exception:
            traceback.print_exc()
            block_f_output = None

        # --- Block G Processing ---
        try:
            block_g_output = os.path.join(output_dir, "output_Block_G.json")

            # Ensure directory exists
            output_dirname = os.path.dirname(block_g_output)
            if output_dirname:
                os.makedirs(output_dirname, exist_ok=True)

            # Step 1: Extract Block G data
            block_g_processor._run_agent(markdown_content, block_g_json_path, block_g_output)
            print(f"✅ Block G extraction completed: {block_g_output}")

            # Step 2: Load extracted Block G
            with open(block_g_output, "r", encoding="utf-8") as f:
                extracted_block_g = json.load(f)
            
            # Load Block D and Block F data for calculations
            block_d_data = None
            block_f_data = None
            
            if block_d_output and os.path.exists(block_d_output):
                with open(block_d_output, "r", encoding="utf-8") as f:
                    block_d_data = json.load(f)
            
            if block_f_output and os.path.exists(block_f_output):
                with open(block_f_output, "r", encoding="utf-8") as f:
                    block_f_data = json.load(f)
            
            # Apply calculations
            g_processor = BlockGJsonProcessor(
                block_g_json=extracted_block_g,
                block_d_json=block_d_data,
                block_f_json=block_f_data
            )
            
            final_block_g = g_processor.process()
            
            # Save the processed Block G
            with open(block_g_output, "w", encoding="utf-8") as f:
                json.dump(final_block_g, f, indent=2)
            
            print(f"✅ Block G post-processing completed: {block_g_output}")

        except Exception:
            traceback.print_exc()
            block_g_output = None

        # --- Block H Processing ---
        try:
            block_h_output = os.path.join(output_dir, "output_Block_H.json")

            # Ensure directory exists
            output_dirname = os.path.dirname(block_h_output)
            if output_dirname:
                os.makedirs(output_dirname, exist_ok=True)

            # Extract Block H data using batch processing
            block_h_processor._run_agent(
                content=markdown_content,
                json_path=block_h_json_path,
                final_path=block_h_output,
                batch_size=5
            )
            print(f"✅ Block H extraction completed: {block_h_output}")

            # Step 2: Apply Block H calculations
            with open(block_h_output, "r", encoding="utf-8") as f:
                extracted_block_h = json.load(f)
            
            # Apply calculations (rate per unit, totals for items 12, 22, 23)
            h_calc_processor = BlockHJsonProcessor(block_h_json=extracted_block_h)
            final_block_h = h_calc_processor.process()
            
            # Save the processed Block H with calculations
            with open(block_h_output, "w", encoding="utf-8") as f:
                json.dump(final_block_h, f, indent=2)
            
            print(f"✅ Block H post-processing (calculations) completed: {block_h_output}")

        except Exception:
            traceback.print_exc()
            block_h_output = None

        # --- BLOCK I PROCESSING ---
        block_i_json_path = "Block_I.json"

        with open(block_i_json_path, "r", encoding="utf-8") as f_i:
            block_i_json = json.load(f_i)

        block_i_dict = block_i_json.get("Block I: Imported input items consumed", {})

        df_i = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_i_dict.items()]
        )
        
        # --- Block J Processing ---
        try:
            block_j_output = os.path.join(output_dir, "output_Block_J.json")

            # Ensure directory exists
            output_dirname = os.path.dirname(block_j_output)
            if output_dirname:
                os.makedirs(output_dirname, exist_ok=True)

            # Extract Block J data
            block_j_processor._run_agent(
                content=markdown_content,
                json_path=block_j_json_path,
                final_path=block_j_output
            )
            print(f"✅ Block J extraction completed: {block_j_output}")

            # Step 2: Apply Block J calculations
            with open(block_j_output, "r", encoding="utf-8") as f:
                extracted_block_j = json.load(f)
            
            # Apply calculations (per unit net sale value, ex-factory value, item 12 total)
            j_calc_processor = BlockJJsonProcessor(block_j_json=extracted_block_j)
            final_block_j = j_calc_processor.process()
            
            # Save the processed Block J with calculations
            with open(block_j_output, "w", encoding="utf-8") as f:
                json.dump(final_block_j, f, indent=2)
            
            print(f"✅ Block J post-processing (calculations) completed: {block_j_output}")

        except Exception:
            traceback.print_exc()
            block_j_output = None

        # --- BLOCK K PROCESSING ---
        block_k_json_path = "Block_K.json"

        with open(block_k_json_path, "r", encoding="utf-8") as f_k:
            block_k_json = json.load(f_k)

        block_k_dict = block_k_json.get("Block K: Information and Communication Technology (ICT) usage", {})

        df_k = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_k_dict.items()]
        )

        # --- BLOCK L PROCESSING ---
        block_l_json_path = "Block_L.json"

        with open(block_l_json_path, "r", encoding="utf-8") as f_l:
            block_l_json = json.load(f_l)

        block_l_dict = block_l_json.get("Block L: Energy Conservation (EC) measures", {})

        df_l = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_l_dict.items()]
        )

        # --- BLOCK M PROCESSING ---
        block_m_json_path = "Block_M.json"

        with open(block_m_json_path, "r", encoding="utf-8") as f_m:
            block_m_json = json.load(f_m)

        block_m_dict = block_m_json.get("Block M: Particulars of field operations", {})

        df_m = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_m_dict.items()]
        )

        # --- BLOCK N PROCESSING ---
        block_n_json_path = "Block_N.json"

        with open(block_n_json_path, "r", encoding="utf-8") as f_n:
            block_n_json = json.load(f_n)

        block_n_dict = block_n_json.get("Block N: Comments of Superintending Officer / Scrutinising Officer", {})

        df_n = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in block_n_dict.items()]
        )
        
        # --- Convert JSONs to Excel ---
        df_c = pd.DataFrame()
        df_d = pd.DataFrame()
        df_e = pd.DataFrame()
        df_f = pd.DataFrame()
        df_g = pd.DataFrame()
        df_h = pd.DataFrame()
        df_j = pd.DataFrame()

        try:
            if complete_json_path_block_c and block_d_output:
                with open(complete_json_path_block_c, "r", encoding="utf-8") as f_c:
                    data_c = json.load(f_c)

                with open(block_d_output, "r", encoding="utf-8") as f_d:
                    data_d = json.load(f_d)

                def get_value(dictionary, *keys):
                    for key in keys:
                        if isinstance(dictionary, dict):
                            dictionary = dictionary.get(key, {})
                        else:
                            return ""
                    return dictionary if isinstance(dictionary, str) else ""

                
                
                # --- Process Block C ---
                rows_c = []
                for asset, details in data_c.get("Type of Assets", {}).items():
                    asset_parts = asset.split('.')
                    sl_no = asset_parts[0]
                    asset_type = asset_parts[1].strip() if len(asset_parts) > 1 else ""

                    row = {
                        "Sl. No.": sl_no,
                        "Type of Assets": asset_type,
                        "Gross value (Rs.) Opening as on (3)": get_value(details, "Gross value (Rs.)", "Opening as on (3)"),
                        "Gross value (Rs.) Due to revaluation (4)": get_value(details, "Gross value (Rs.)", "Addition during the year", "Due to revaluation (4)"),
                        "Gross value (Rs.) Actual additions (5)": get_value(details, "Gross value (Rs.)", "Addition during the year", "Actual additions (5)"),
                        "Gross value (Rs.) Deduction & adjustment during the year(6)": get_value(details, "Gross value (Rs.)", "Deduction & adjustment during the year(6)"),
                        "Gross value (Rs.) Closing as on (cols. 3+4+5-6) (7)": get_value(details, "Gross value (Rs.)", "Closing as on (cols. 3+4+5-6) (7)"),
                        "Depreciation (Rs.) Up to year beginning (8)": get_value(details, "Depreciation (Rs.)", "Up to year beginning (8)"),
                        "Depreciation (Rs.) Provided during the year (9)": get_value(details, "Depreciation (Rs.)", "Provided during the year (9)"),
                        "Depreciation (Rs.) Adjustment for sold/ discarded during the year (10)": get_value(details, "Depreciation (Rs.)", "Adjustment for sold/ discarded during the year (10)"),
                        "Depreciation (Rs.) Up to year end (cols.8+9 -10) (11)": get_value(details, "Depreciation (Rs.)", "Up to year end (cols.8+9 -10) (11)"),
                        "Net value (Rs.) Opening as on ----- (cols. 3-8) (12)": get_value(details, "Net value (Rs.)", "Opening as on ----- (cols. 3-8) (12)"),
                        "Net value (Rs.) Closing as on ------ (cols. 7- 11) (13)": get_value(details, "Net value (Rs.)", "Closing as on ------ (cols. 7- 11) (13)")
                    }
                    rows_c.append(row)

                df_c = pd.DataFrame(rows_c)

                # --- Process Block D ---
                rows_d = []
                for asset, details in data_d.get("Block D: WORKING CAPITAL AND LOANS", {}).items():
                    asset_name = asset.split('(')[0].strip()
                    row = {
                        "Asset Name": asset_name,
                        "Opening (Rs.)": details.get("Opening (Rs.)", ""),
                        "Closing (Rs.)": details.get("Closing (Rs.)", "")
                    }
                    rows_d.append(row)

                df_d = pd.DataFrame(rows_d)

                # --- Process Block E ---
                if block_e_output and os.path.exists(block_e_output):
                    with open(block_e_output, "r", encoding="utf-8") as f_e:
                        data_e = json.load(f_e)

                    rows_e = []
                
                    part_b = data_e.get("Block E: EMPLOYMENT AND LABOUR COST - Part B", {}) \
                                .get("Part B: Some details for all categories of staff combined", {})
                
                    # Item 11: Bonus
                    item_11 = part_b.get("11. Bonus (in Rs.)", "")
                    rows_e.append({
                        "Item No.": "11",
                        "Description": "Bonus",
                        "Amount (Rs.)": item_11
                    })

                    # Item 12: Contribution to PF & other funds
                    item_12 = part_b.get("12. Contribution to provident & other funds (in Rs.)", "")
                    rows_e.append({
                        "Item No.": "12",
                        "Description": "Contribution to provident & other funds",
                        "Amount (Rs.)": item_12
                    })
                
                    df_e = pd.DataFrame(rows_e)

                # --- Process Block F ---
                if block_f_output and os.path.exists(block_f_output):
                    with open(block_f_output, "r", encoding="utf-8") as f_f:
                        data_f = json.load(f_f)

                    rows_f = []
                    for item_key, item_data in data_f.get("Block F: OTHER EXPENSES", {}).items():
                        # Extract serial number and item name
                        item_name = item_key.split('.', 1)[1].strip() if '.' in item_key else item_key
                        
                        # Handle nested structure for "Repair & maintenance"
                        if isinstance(item_data, dict):
                            if "Expenditure (Rs.)" in item_data:
                                # Direct expenditure item
                                row = {
                                    "Item": item_name,
                                    "Expenditure (Rs.)": item_data.get("Expenditure (Rs.)", "")
                                }
                                rows_f.append(row)
                            else:
                                # Nested items (like Repair & maintenance)
                                for sub_key, sub_data in item_data.items():
                                    if isinstance(sub_data, dict):
                                        row = {
                                            "Item": f"{item_name} - {sub_key}",
                                            "Expenditure (Rs.)": sub_data.get("Expenditure (Rs.)", "")
                                        }
                                        rows_f.append(row)

                    df_f = pd.DataFrame(rows_f)

                # --- Process Block G ---
                if block_g_output and os.path.exists(block_g_output):
                    with open(block_g_output, "r", encoding="utf-8") as f_g:
                        data_g = json.load(f_g)

                    rows_g = []
                    for item_key, item_data in data_g.get("Block G: OTHER OUTPUT/RECEIPTS", {}).items():
                        # Extract serial number and item name
                        item_name = item_key.split('.', 1)[1].strip() if '.' in item_key else item_key
                        
                        # Extract receipts value
                        if isinstance(item_data, dict):
                            row = {
                                "Item": item_name,
                                "Receipts (Rs.)": item_data.get("Receipts (Rs.)", "")
                            }
                            rows_g.append(row)

                    df_g = pd.DataFrame(rows_g)

                # --- Process Block H ---
                if block_h_output and os.path.exists(block_h_output):
                    with open(block_h_output, "r", encoding="utf-8") as f_h:
                        data_h = json.load(f_h)

                    rows_h = []
                    for item_key, item_data in data_h.get("Block H: Indigenous input items consumed", {}).items():
                        # Extract serial number and item name
                        item_number = item_key.rstrip('.')
                        
                        # Extract all fields
                        if isinstance(item_data, dict):
                            row = {
                                "Sl. No.": item_number,
                                "Item description": item_data.get("Item description", ""),
                                "Item code (NPC-MS)": item_data.get("Item code (NPC-MS)", ""),
                                "Unit of quantity": item_data.get("Unit of quantity", ""),
                                "Quantity consumed": item_data.get("Quantity consumed", ""),
                                "Purchase value (Rs.)": item_data.get("Purchase value (Rs.)", ""),
                                "Rate per unit (Rs.)": item_data.get("Rate per unit (Rs.)", "")
                            }
                            rows_h.append(row)

                    df_h = pd.DataFrame(rows_h)

                # --- Process Block J ---
                if block_j_output and os.path.exists(block_j_output):
                    with open(block_j_output, "r", encoding="utf-8") as f_j:
                        data_j = json.load(f_j)

                    rows_j = []
                    for item_key, item_data in data_j.get("Block J: Products and by-products manufactured by the unit", {}).items():
                        # Extract item number and description
                        item_number = item_key.split('.')[0] if '.' in item_key else ""
                        
                        # Extract all fields
                        if isinstance(item_data, dict):
                            # Handle distributive expenses
                            dist_expenses = item_data.get("Distributive expenses (Rs.)", {})
                            
                            row = {
                                "Sl. No.": item_number,
                                "Item description": item_data.get("Item description", ""),
                                "Item code (NPCMS)": item_data.get("Item code (NPCMS)", ""),
                                "Unit of quantity": item_data.get("Unit of quantity", ""),
                                "Quantity manufactured": item_data.get("Quantity manufactured", ""),
                                "Quantity sold": item_data.get("Quantity sold", ""),
                                "Gross sale value (Rs.)": item_data.get("Gross sale value (Rs.)", ""),
                                "GST": dist_expenses.get("Goods and Services Tax(GST)", "") if isinstance(dist_expenses, dict) else "",
                                "Excise Duty/Sales Tax/VAT": dist_expenses.get("Excise Duty/Sales Tax/VAT/Other Taxes, if any", "") if isinstance(dist_expenses, dict) else "",
                                "Other Distributive Expenses": dist_expenses.get("Other Distributive Expenses", "") if isinstance(dist_expenses, dict) else "",
                                "Subsidy (-)": dist_expenses.get("Subsidy (-)", "") if isinstance(dist_expenses, dict) else "",
                                "Per unit net sale value (Rs.)": item_data.get("Per unit net sale value (Rs. 0.00)", ""),
                                "Ex-factory value (Rs.)": item_data.get("Ex-factory value of quantity manufactured (Rs.)", "")
                            }
                            rows_j.append(row)
                    
                    # Add export share if present
                    export_share = data_j.get("Block J: Products and by-products manufactured by the unit", {}).get("13. Share (%) of products/by-products directly exported", "")
                    if export_share:
                        rows_j.append({
                            "Sl. No.": "13",
                            "Item description": "Share (%) of products/by-products directly exported",
                            "Item code (NPCMS)": "",
                            "Unit of quantity": "%",
                            "Quantity manufactured": "",
                            "Quantity sold": "",
                            "Gross sale value (Rs.)": "",
                            "GST": "",
                            "Excise Duty/Sales Tax/VAT": "",
                            "Other Distributive Expenses": "",
                            "Subsidy (-)": "",
                            "Per unit net sale value (Rs.)": "",
                            "Ex-factory value (Rs.)": export_share
                        })

                    df_j = pd.DataFrame(rows_j)

                # Create Excel with all blocks
                excel_output_path = os.path.join(output_dir, "block_output_combined.xlsx")
                with pd.ExcelWriter(excel_output_path) as writer:
                    df_a.to_excel(writer, sheet_name="Block A", index=False)
                    df_b.to_excel(writer, sheet_name="Block B", index=False)
                    df_c.to_excel(writer, sheet_name="Block C", index=False)
                    df_d.to_excel(writer, sheet_name="Block D", index=False)
                    if not df_e.empty:
                        df_e.to_excel(writer, sheet_name="Block E", index=False)
                    if not df_f.empty:
                        df_f.to_excel(writer, sheet_name="Block F", index=False)
                    if not df_g.empty:
                        df_g.to_excel(writer, sheet_name="Block G", index=False)
                    if not df_h.empty:
                        df_h.to_excel(writer, sheet_name="Block H", index=False)
                    df_i.to_excel(writer, sheet_name="Block I", index=False)    
                    if not df_j.empty:
                        df_j.to_excel(writer, sheet_name="Block J", index=False)
                    df_k.to_excel(writer, sheet_name="Block K", index=False)
                    df_l.to_excel(writer, sheet_name="Block L", index=False)
                    df_m.to_excel(writer, sheet_name="Block M", index=False)
                    df_n.to_excel(writer, sheet_name="Block N", index=False)    

        except Exception:
            traceback.print_exc()

        return {
            "message": "✅ Processing Complete",
            "excel_available": not df_c.empty and not df_d.empty,
            "block_a_data": df_a.to_dict(orient="records"),
            "block_b_data": df_b.to_dict(orient="records"),
            "block_c_data": df_c.to_dict(orient="records") if not df_c.empty else [],
            "block_d_data": df_d.to_dict(orient="records") if not df_d.empty else [],
            "block_e_data": df_e.to_dict(orient="records") if not df_e.empty else [],
            "block_f_data": df_f.to_dict(orient="records") if not df_f.empty else [],
            "block_g_data": df_g.to_dict(orient="records") if not df_g.empty else [],
            "block_h_data": df_h.to_dict(orient="records") if not df_h.empty else [],
            "block_i_data": df_i.to_dict(orient="records"),
            "block_j_data": df_j.to_dict(orient="records") if not df_j.empty else [],
            "block_k_data": df_k.to_dict(orient="records"),
            "block_l_data": df_l.to_dict(orient="records"),
            "block_m_data": df_m.to_dict(orient="records"),
            "block_n_data": df_n.to_dict(orient="records")
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

    

@app.get("/download_excel")
def download_excel():
    excel_file = upload_dir +"/Outputs/block_output_combined.xlsx"
    print("Excel File :", excel_file)
    if not os.path.exists(excel_file):
        return JSONResponse(status_code=404, content={"error": "Excel file not found."})
    return FileResponse(path=excel_file, filename="block_output_combined.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")