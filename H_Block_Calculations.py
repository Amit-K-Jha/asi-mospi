import json
import copy

class BlockHJsonProcessor:
    """
    Processor for Block H: Indigenous input items consumed
    Handles calculations:
    - Item 12: Total basic items (sum of items 1-11)
    - Item 22: Total non-basic items (sum of items 13-21)
    - Item 23: Total inputs (item 12 + item 22)
    - Rate per unit for each item = Purchase value ÷ Quantity consumed
    """
    
    def __init__(self, block_h_json):
        """
        Initialize the processor with Block H data.
        
        Args:
            block_h_json: The filled Block H JSON from extraction
        """
        self.block_h_json = copy.deepcopy(block_h_json)
    
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
    
    @staticmethod
    def format_number(value):
        """Format number as string with 2 decimal places, return empty string if zero."""
        if value == 0.0:
            return ""
        return f"{value:.2f}"
    
    def calculate_rate_per_unit(self, item_data):
        """
        Calculate rate per unit = Purchase value ÷ Quantity consumed
        
        Args:
            item_data: Dictionary containing item fields
            
        Returns:
            Calculated rate as formatted string
        """
        purchase_value = self.safe_float(item_data.get("Purchase value (Rs.)", ""))
        quantity = self.safe_float(item_data.get("Quantity consumed", ""))
        
        if quantity == 0:
            return ""
        
        rate = purchase_value / quantity
        return self.format_number(rate)
    
    def sum_items(self, items, field):
        """
        Sum a specific field across multiple items.
        
        Args:
            items: List of item keys
            field: Field name to sum
            
        Returns:
            Sum as formatted string
        """
        block_h_data = self.block_h_json.get("Block H: Indigenous input items consumed", {})
        total = 0.0
        
        for item_key in items:
            # Find the item in block_h_data
            for key in block_h_data.keys():
                if key.startswith(f"{item_key}."):
                    item_data = block_h_data[key]
                    value = self.safe_float(item_data.get(field, ""))
                    total += value
                    break
        
        return self.format_number(total)
    
    def calculate_item_12_total_basic(self):
        """
        Calculate Item 12: Total basic items (sum of items 1-11)
        """
        items = list(range(1, 12))  # Items 1 to 11
        
        print(f"📊 Item 12 Calculation (Total basic items):")
        
        # Calculate for each field
        quantity = self.sum_items(items, "Quantity consumed")
        purchase_value = self.sum_items(items, "Purchase value (Rs.)")
        
        # Calculate rate per unit for total
        qty_val = self.safe_float(quantity)
        purch_val = self.safe_float(purchase_value)
        rate = ""
        if qty_val > 0:
            rate = self.format_number(purch_val / qty_val)
        
        print(f"   Quantity consumed: {quantity}")
        print(f"   Purchase value: {purchase_value}")
        print(f"   Rate per unit: {rate}")
        
        return {
            "Quantity consumed": quantity,
            "Purchase value (Rs.)": purchase_value,
            "Rate per unit (Rs.)": rate
        }
    
    def calculate_item_22_total_non_basic(self):
        """
        Calculate Item 22: Total non-basic items (sum of items 13-21)
        """
        items = list(range(13, 22))  # Items 13 to 21
        
        print(f"📊 Item 22 Calculation (Total non-basic items):")
        
        # Calculate for each field
        quantity = self.sum_items(items, "Quantity consumed")
        purchase_value = self.sum_items(items, "Purchase value (Rs.)")
        
        # Calculate rate per unit for total
        qty_val = self.safe_float(quantity)
        purch_val = self.safe_float(purchase_value)
        rate = ""
        if qty_val > 0:
            rate = self.format_number(purch_val / qty_val)
        
        print(f"   Quantity consumed: {quantity}")
        print(f"   Purchase value: {purchase_value}")
        print(f"   Rate per unit: {rate}")
        
        return {
            "Quantity consumed": quantity,
            "Purchase value (Rs.)": purchase_value,
            "Rate per unit (Rs.)": rate
        }
    
    def calculate_item_23_total_inputs(self):
        """
        Calculate Item 23: Total inputs (item 12 + item 22)
        """
        block_h_data = self.block_h_json.get("Block H: Indigenous input items consumed", {})
        
        print(f"📊 Item 23 Calculation (Total inputs):")
        
        # Get item 12 and 22 data
        item_12_data = None
        item_22_data = None
        
        for key in block_h_data.keys():
            if key.startswith("12."):
                item_12_data = block_h_data[key]
            elif key.startswith("22."):
                item_22_data = block_h_data[key]
        
        if not item_12_data or not item_22_data:
            print("   ⚠️ Item 12 or 22 not found")
            return {
                "Quantity consumed": "",
                "Purchase value (Rs.)": "",
                "Rate per unit (Rs.)": ""
            }
        
        # Sum quantities and purchase values
        qty_12 = self.safe_float(item_12_data.get("Quantity consumed", ""))
        qty_22 = self.safe_float(item_22_data.get("Quantity consumed", ""))
        total_qty = qty_12 + qty_22
        
        purch_12 = self.safe_float(item_12_data.get("Purchase value (Rs.)", ""))
        purch_22 = self.safe_float(item_22_data.get("Purchase value (Rs.)", ""))
        total_purch = purch_12 + purch_22
        
        # Calculate rate
        rate = ""
        if total_qty > 0:
            rate = self.format_number(total_purch / total_qty)
        
        print(f"   Quantity consumed: {self.format_number(total_qty)}")
        print(f"   Purchase value: {self.format_number(total_purch)}")
        print(f"   Rate per unit: {rate}")
        
        return {
            "Quantity consumed": self.format_number(total_qty),
            "Purchase value (Rs.)": self.format_number(total_purch),
            "Rate per unit (Rs.)": rate
        }
    
    def fill_calculated_fields(self):
        """
        Fill all calculated fields in Block H JSON.
        Returns the updated Block H JSON.
        """
        block_h_data = self.block_h_json.get("Block H: Indigenous input items consumed", {})
        
        # Calculate rate per unit for all items (1-21, excluding totals)
        print("\n📊 Calculating rates per unit for individual items:")
        for key in list(block_h_data.keys()):
            # Extract item number
            item_num_str = key.split('.')[0]
            try:
                item_num = int(item_num_str)
                # Calculate rate for items 1-21 (not totals 12, 22, 23)
                if 1 <= item_num <= 21 and item_num not in [12, 22]:
                    item_data = block_h_data[key]
                    current_rate = item_data.get("Rate per unit (Rs.)", "")
                    
                    if not current_rate or current_rate == "":
                        calculated_rate = self.calculate_rate_per_unit(item_data)
                        if calculated_rate:
                            block_h_data[key]["Rate per unit (Rs.)"] = calculated_rate
                            print(f"   ✅ Item {item_num}: Rate = {calculated_rate}")
            except ValueError:
                pass
        
        # Calculate Item 12: Total basic items
        item_12_key = None
        for key in block_h_data.keys():
            if key.startswith("12."):
                item_12_key = key
                break
        
        if item_12_key:
            item_12_calcs = self.calculate_item_12_total_basic()
            for field, value in item_12_calcs.items():
                if value:  # Only update if value is not empty
                    block_h_data[item_12_key][field] = value
            print(f"✅ Updated Item 12 (Total basic items)")
        
        # Calculate Item 22: Total non-basic items
        item_22_key = None
        for key in block_h_data.keys():
            if key.startswith("22."):
                item_22_key = key
                break
        
        if item_22_key:
            item_22_calcs = self.calculate_item_22_total_non_basic()
            for field, value in item_22_calcs.items():
                if value:  # Only update if value is not empty
                    block_h_data[item_22_key][field] = value
            print(f"✅ Updated Item 22 (Total non-basic items)")
        
        # Calculate Item 23: Total inputs
        item_23_key = None
        for key in block_h_data.keys():
            if key.startswith("23."):
                item_23_key = key
                break
        
        if item_23_key:
            item_23_calcs = self.calculate_item_23_total_inputs()
            for field, value in item_23_calcs.items():
                if value:  # Only update if value is not empty
                    block_h_data[item_23_key][field] = value
            print(f"✅ Updated Item 23 (Total inputs)")
        
        self.block_h_json["Block H: Indigenous input items consumed"] = block_h_data
        return self.block_h_json
    
    def process(self):
        """
        Main processing method - fills all calculated fields.
        """
        print("\n" + "="*50)
        print("Starting Block H Post-Processing (Calculations)")
        print("="*50)
        
        result = self.fill_calculated_fields()
        
        print("\n" + "="*50)
        print("Block H Post-Processing Complete")
        print("="*50 + "\n")
        
        return result


# Example usage
if __name__ == "__main__":
    # Example data
    block_h = {
        "Block H: Indigenous input items consumed": {
            "1. Item 1": {
                "Item description": "Steel",
                "Item code (NPC-MS)": "12345",
                "Unit of quantity": "Kg",
                "Quantity consumed": "1000",
                "Purchase value (Rs.)": "50000",
                "Rate per unit (Rs.)": ""
            },
            "2. Item 2": {
                "Item description": "Copper",
                "Item code (NPC-MS)": "12346",
                "Unit of quantity": "Kg",
                "Quantity consumed": "500",
                "Purchase value (Rs.)": "30000",
                "Rate per unit (Rs.)": ""
            },
            "12. Total basic items": {
                "Item description": "Total basic items",
                "Item code (NPC-MS)": "9990100",
                "Unit of quantity": "",
                "Quantity consumed": "",
                "Purchase value (Rs.)": "",
                "Rate per unit (Rs.)": ""
            },
            "13. Non-basic chemicals": {
                "Item description": "Chemicals",
                "Item code (NPC-MS)": "9920300",
                "Unit of quantity": "Litre",
                "Quantity consumed": "200",
                "Purchase value (Rs.)": "10000",
                "Rate per unit (Rs.)": ""
            },
            "22. Total non-basic items": {
                "Item description": "Total non-basic items",
                "Item code (NPC-MS)": "9992000",
                "Unit of quantity": "",
                "Quantity consumed": "",
                "Purchase value (Rs.)": "",
                "Rate per unit (Rs.)": ""
            },
            "23. Total inputs": {
                "Item description": "Total inputs",
                "Item code (NPC-MS)": "9993000",
                "Unit of quantity": "",
                "Quantity consumed": "",
                "Purchase value (Rs.)": "",
                "Rate per unit (Rs.)": ""
            }
        }
    }
    
    # Process
    processor = BlockHJsonProcessor(block_h_json=block_h)
    result = processor.process()
    
    print("\nFinal Block H JSON:")
    print(json.dumps(result, indent=2))