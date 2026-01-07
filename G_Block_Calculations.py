import json
import copy

class BlockGJsonProcessor:
    """
    Processor for Block G: OTHER OUTPUT/RECEIPTS
    Handles calculations that depend on other blocks:
    - Item 5: Net balance (Block G Item 11 - Block F Item 11)
    - Item 7: Stock variation (Block D Item 5 Closing - Opening)
    """
    
    def __init__(self, block_g_json, block_d_json=None, block_f_json=None):
        """
        Initialize the processor with Block G data and optional Block D and F data.
        
        Args:
            block_g_json: The filled Block G JSON from extraction
            block_d_json: Block D JSON (needed for item 7 calculation)
            block_f_json: Block F JSON (needed for item 5 calculation)
        """
        self.block_g_json = copy.deepcopy(block_g_json)
        self.block_d_json = block_d_json
        self.block_f_json = block_f_json
    
    @staticmethod
    def safe_float(value):
        """Safely converts a value to float, returning 0 if it's not a valid number."""
        if value is None or value == "":
            return 0.0
        try:
            # Remove commas and convert to float
            if isinstance(value, str):
                value = value.replace(",", "").strip()
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def calculate_item_5_net_balance(self):
        """
        Calculate Item 5: Net balance of goods sold in same condition as purchased
        Formula: Block G Item 11 - Block F Item 11
        """
        if not self.block_f_json:
            print("⚠️ Block F data not provided. Skipping Item 5 calculation.")
            return None
        
        block_g_data = self.block_g_json.get("Block G: OTHER OUTPUT/RECEIPTS", {})
        block_f_data = self.block_f_json.get("Block F: OTHER EXPENSES", {})
        
        # Find Item 11 in Block G (Sale value)
        g_item_11_key = None
        for key in block_g_data.keys():
            if key.startswith("11."):
                g_item_11_key = key
                break
        
        # Find Item 11 in Block F (Purchase value)
        f_item_11_key = None
        for key in block_f_data.keys():
            if key.startswith("11."):
                f_item_11_key = key
                break
        
        if not g_item_11_key or not f_item_11_key:
            print("⚠️ Could not find Item 11 in Block G or Block F")
            return None
        
        # Get values
        g_sale_value = block_g_data[g_item_11_key].get("Receipts (Rs.)", "")
        f_purchase_value = block_f_data[f_item_11_key].get("Expenditure (Rs.)", "")
        
        # Calculate net balance
        sale = self.safe_float(g_sale_value)
        purchase = self.safe_float(f_purchase_value)
        net_balance = sale - purchase
        
        print(f"📊 Item 5 Calculation:")
        print(f"   Sale Value (G-11): {sale}")
        print(f"   Purchase Value (F-11): {purchase}")
        print(f"   Net Balance: {net_balance}")
        
        # Return as string with 2 decimal places, preserve sign
        return f"{net_balance:.2f}" if net_balance != 0 else ""
    
    def calculate_item_7_stock_variation(self):
        """
        Calculate Item 7: Variation in stock of semi-finished goods
        Formula: Block D Item 5 Closing - Block D Item 5 Opening
        """
        if not self.block_d_json:
            print("⚠️ Block D data not provided. Skipping Item 7 calculation.")
            return None
        
        block_d_data = self.block_d_json.get("Block D: WORKING CAPITAL AND LOANS", {})
        
        # Find Item 5 in Block D (Semi-finished goods/work in progress)
        d_item_5_key = None
        for key in block_d_data.keys():
            if key.startswith("5."):
                d_item_5_key = key
                break
        
        if not d_item_5_key:
            print("⚠️ Could not find Item 5 in Block D")
            return None
        
        # Get opening and closing values
        opening = block_d_data[d_item_5_key].get("Opening (Rs.)", "")
        closing = block_d_data[d_item_5_key].get("Closing (Rs.)", "")
        
        # Calculate variation
        opening_val = self.safe_float(opening)
        closing_val = self.safe_float(closing)
        variation = closing_val - opening_val
        
        print(f"📊 Item 7 Calculation:")
        print(f"   Opening (D-5): {opening_val}")
        print(f"   Closing (D-5): {closing_val}")
        print(f"   Variation: {variation}")
        
        # Return as string with 2 decimal places, preserve sign
        return f"{variation:.2f}" if variation != 0 else ""
    
    def fill_calculated_fields(self):
        """
        Fill the calculated fields in Block G JSON.
        Returns the updated Block G JSON.
        """
        block_g_data = self.block_g_json.get("Block G: OTHER OUTPUT/RECEIPTS", {})
        
        # Calculate and fill Item 5
        item_5_key = None
        for key in block_g_data.keys():
            if key.startswith("5."):
                item_5_key = key
                break
        
        if item_5_key:
            # Only calculate if field is empty or we want to override
            current_value = block_g_data[item_5_key].get("Receipts (Rs.)", "")
            if not current_value or current_value == "":
                calculated_value = self.calculate_item_5_net_balance()
                if calculated_value is not None:
                    block_g_data[item_5_key]["Receipts (Rs.)"] = calculated_value
                    print(f"✅ Updated Item 5 with calculated value: {calculated_value}")
            else:
                print(f"ℹ️ Item 5 already has value: {current_value} (skipping calculation)")
        
        # Calculate and fill Item 7
        item_7_key = None
        for key in block_g_data.keys():
            if key.startswith("7."):
                item_7_key = key
                break
        
        if item_7_key:
            # Only calculate if field is empty or we want to override
            current_value = block_g_data[item_7_key].get("Receipts (Rs.)", "")
            if not current_value or current_value == "":
                calculated_value = self.calculate_item_7_stock_variation()
                if calculated_value is not None:
                    block_g_data[item_7_key]["Receipts (Rs.)"] = calculated_value
                    print(f"✅ Updated Item 7 with calculated value: {calculated_value}")
            else:
                print(f"ℹ️ Item 7 already has value: {current_value} (skipping calculation)")
        
        self.block_g_json["Block G: OTHER OUTPUT/RECEIPTS"] = block_g_data
        return self.block_g_json
    
    def process(self):
        """
        Main processing method - fills all calculated fields.
        """
        print("\n" + "="*50)
        print("Starting Block G Post-Processing")
        print("="*50)
        
        result = self.fill_calculated_fields()
        
        print("\n" + "="*50)
        print("Block G Post-Processing Complete")
        print("="*50 + "\n")
        
        return result


# Example usage
if __name__ == "__main__":
    # Example data
    block_g = {
        "Block G: OTHER OUTPUT/RECEIPTS": {
            "5. Net balance of goods sold in the same condition as purchased": {
                "Receipts (Rs.)": ""
            },
            "7. Variation in stock of semi-finished goods": {
                "Receipts (Rs.)": ""
            },
            "11. Sale value of goods sold in the same condition as purchased": {
                "Receipts (Rs.)": "50000"
            }
        }
    }
    
    block_d = {
        "Block D: WORKING CAPITAL AND LOANS": {
            "5. Semi-finished goods/work in progress": {
                "Opening (Rs.)": "20000",
                "Closing (Rs.)": "25000"
            }
        }
    }
    
    block_f = {
        "Block F: OTHER EXPENSES": {
            "11. Purchase value of goods sold in the same condition as purchased": {
                "Expenditure (Rs.)": "45000"
            }
        }
    }
    
    # Process
    processor = BlockGJsonProcessor(
        block_g_json=block_g,
        block_d_json=block_d,
        block_f_json=block_f
    )
    
    result = processor.process()
    
    print("\nFinal Block G JSON:")
    print(json.dumps(result, indent=2))