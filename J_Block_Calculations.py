import json
import copy

class BlockJJsonProcessor:
    """
    Processor for Block J: Products and by-products manufactured by the unit
    Handles calculations:
    - Item 12: Total (sum of items 1-11) for all columns
    - Per unit net sale value (col 12) = (col 7 - [col 8 + col 9 + col 10 - col 11]) ÷ col 6
    - Ex-factory value (col 13) = col 12 × col 5
    
    Formula details:
    - Per unit net sale value = (Gross sale value - [GST + Excise/VAT + Other Expenses - Subsidy]) ÷ Quantity sold
    - Ex-factory value = Per unit net sale value × Quantity manufactured
    """
    
    def __init__(self, block_j_json):
        """
        Initialize the processor with Block J data.
        
        Args:
            block_j_json: The filled Block J JSON from extraction
        """
        self.block_j_json = copy.deepcopy(block_j_json)
    
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
    
    def calculate_per_unit_net_sale_value(self, item_data):
        """
        Calculate per unit net sale value.
        Formula: (Gross sale value - [GST + Excise/VAT + Other Expenses - Subsidy]) ÷ Quantity sold
        
        Args:
            item_data: Dictionary containing item fields
            
        Returns:
            Calculated per unit net sale value as formatted string
        """
        gross_sale = self.safe_float(item_data.get("Gross sale value (Rs.)", ""))
        quantity_sold = self.safe_float(item_data.get("Quantity sold", ""))
        
        # Get distributive expenses
        dist_expenses = item_data.get("Distributive expenses (Rs.)", {})
        if isinstance(dist_expenses, dict):
            gst = self.safe_float(dist_expenses.get("Goods and Services Tax(GST)", ""))
            excise_vat = self.safe_float(dist_expenses.get("Excise Duty/Sales Tax/VAT/Other Taxes, if any", ""))
            other_expenses = self.safe_float(dist_expenses.get("Other Distributive Expenses", ""))
            subsidy = self.safe_float(dist_expenses.get("Subsidy (-)", ""))
        else:
            gst = 0.0
            excise_vat = 0.0
            other_expenses = 0.0
            subsidy = 0.0
        
        if quantity_sold == 0:
            return ""
        
        # Calculate: (Gross sale - [GST + Excise/VAT + Other - Subsidy]) / Quantity sold
        net_value = gross_sale - (gst + excise_vat + other_expenses - subsidy)
        per_unit = net_value / quantity_sold
        
        return self.format_number(per_unit)
    
    def calculate_ex_factory_value(self, item_data):
        """
        Calculate ex-factory value.
        Formula: Per unit net sale value × Quantity manufactured
        
        Args:
            item_data: Dictionary containing item fields
            
        Returns:
            Calculated ex-factory value as formatted string
        """
        per_unit = self.safe_float(item_data.get("Per unit net sale value (Rs. 0.00)", ""))
        quantity_mfg = self.safe_float(item_data.get("Quantity manufactured", ""))
        
        if per_unit == 0 or quantity_mfg == 0:
            return ""
        
        ex_factory = per_unit * quantity_mfg
        return self.format_number(ex_factory)
    
    def sum_items_for_total(self):
        """
        Calculate Item 12: Total (sum of items 1-11) for all columns.
        
        Returns:
            Dictionary with totals for each field
        """
        block_j_data = self.block_j_json.get("Block J: Products and by-products manufactured by the unit", {})
        
        print(f"📊 Item 12 Calculation (Total of items 1-11):")
        
        # Fields to sum
        sum_fields = [
            "Quantity manufactured",
            "Quantity sold",
            "Gross sale value (Rs.)"
        ]
        
        dist_expense_fields = [
            "Goods and Services Tax(GST)",
            "Excise Duty/Sales Tax/VAT/Other Taxes, if any",
            "Other Distributive Expenses",
            "Subsidy (-)"
        ]
        
        # Initialize totals
        totals = {field: 0.0 for field in sum_fields}
        dist_totals = {field: 0.0 for field in dist_expense_fields}
        
        # Sum items 1-11
        for item_num in range(1, 12):
            for key in block_j_data.keys():
                if key.startswith(f"{item_num}."):
                    item_data = block_j_data[key]
                    
                    # Sum regular fields
                    for field in sum_fields:
                        value = self.safe_float(item_data.get(field, ""))
                        totals[field] += value
                    
                    # Sum distributive expenses
                    dist_expenses = item_data.get("Distributive expenses (Rs.)", {})
                    if isinstance(dist_expenses, dict):
                        for field in dist_expense_fields:
                            value = self.safe_float(dist_expenses.get(field, ""))
                            dist_totals[field] += value
                    break
        
        # Format totals
        result = {
            "Quantity manufactured": self.format_number(totals["Quantity manufactured"]),
            "Quantity sold": self.format_number(totals["Quantity sold"]),
            "Gross sale value (Rs.)": self.format_number(totals["Gross sale value (Rs.)"]),
            "Distributive expenses (Rs.)": {
                field: self.format_number(dist_totals[field])
                for field in dist_expense_fields
            }
        }
        
        # Calculate per unit and ex-factory for total
        # Create temporary item data for calculation
        temp_item = {
            "Quantity manufactured": result["Quantity manufactured"],
            "Quantity sold": result["Quantity sold"],
            "Gross sale value (Rs.)": result["Gross sale value (Rs.)"],
            "Distributive expenses (Rs.)": result["Distributive expenses (Rs.)"]
        }
        
        per_unit = self.calculate_per_unit_net_sale_value(temp_item)
        if per_unit:
            temp_item["Per unit net sale value (Rs. 0.00)"] = per_unit
            ex_factory = self.calculate_ex_factory_value(temp_item)
            result["Per unit net sale value (Rs. 0.00)"] = per_unit
            result["Ex-factory value of quantity manufactured (Rs.)"] = ex_factory
        else:
            result["Per unit net sale value (Rs. 0.00)"] = ""
            result["Ex-factory value of quantity manufactured (Rs.)"] = ""
        
        print(f"   Quantity manufactured: {result['Quantity manufactured']}")
        print(f"   Quantity sold: {result['Quantity sold']}")
        print(f"   Gross sale value: {result['Gross sale value (Rs.)']}")
        print(f"   Per unit net sale value: {result['Per unit net sale value (Rs. 0.00)']}")
        print(f"   Ex-factory value: {result['Ex-factory value of quantity manufactured (Rs.)']}")
        
        return result
    
    def fill_calculated_fields(self):
        """
        Fill all calculated fields in Block J JSON.
        Returns the updated Block J JSON.
        """
        block_j_data = self.block_j_json.get("Block J: Products and by-products manufactured by the unit", {})
        
        # Calculate per unit and ex-factory for individual items (1-11)
        print("\n📊 Calculating per unit and ex-factory values for individual items:")
        for key in list(block_j_data.keys()):
            # Extract item number
            item_num_str = key.split('.')[0]
            try:
                item_num = int(item_num_str)
                # Calculate for items 1-11 (not total 12)
                if 1 <= item_num <= 11:
                    item_data = block_j_data[key]
                    
                    # Calculate per unit net sale value
                    current_per_unit = item_data.get("Per unit net sale value (Rs. 0.00)", "")
                    if not current_per_unit or current_per_unit == "":
                        calculated_per_unit = self.calculate_per_unit_net_sale_value(item_data)
                        if calculated_per_unit:
                            block_j_data[key]["Per unit net sale value (Rs. 0.00)"] = calculated_per_unit
                            print(f"   ✅ Item {item_num}: Per unit = {calculated_per_unit}")
                            
                            # Also calculate ex-factory value
                            item_data["Per unit net sale value (Rs. 0.00)"] = calculated_per_unit
                            calculated_ex_factory = self.calculate_ex_factory_value(item_data)
                            if calculated_ex_factory:
                                block_j_data[key]["Ex-factory value of quantity manufactured (Rs.)"] = calculated_ex_factory
                                print(f"   ✅ Item {item_num}: Ex-factory = {calculated_ex_factory}")
                    else:
                        # If per unit exists, calculate ex-factory
                        current_ex_factory = item_data.get("Ex-factory value of quantity manufactured (Rs.)", "")
                        if not current_ex_factory or current_ex_factory == "":
                            calculated_ex_factory = self.calculate_ex_factory_value(item_data)
                            if calculated_ex_factory:
                                block_j_data[key]["Ex-factory value of quantity manufactured (Rs.)"] = calculated_ex_factory
                                print(f"   ✅ Item {item_num}: Ex-factory = {calculated_ex_factory}")
            except ValueError:
                pass
        
        # Calculate Item 12: Total
        item_12_key = None
        for key in block_j_data.keys():
            if key.startswith("12."):
                item_12_key = key
                break
        
        if item_12_key:
            item_12_calcs = self.sum_items_for_total()
            # Update all fields except Item description and Item code
            for field, value in item_12_calcs.items():
                if field in ["Item description", "Item code (NPCMS)", "Unit of quantity"]:
                    continue  # Skip these fields
                if value:  # Only update if value is not empty
                    block_j_data[item_12_key][field] = value
            print(f"✅ Updated Item 12 (Total)")
        
        self.block_j_json["Block J: Products and by-products manufactured by the unit"] = block_j_data
        return self.block_j_json
    
    def process(self):
        """
        Main processing method - fills all calculated fields.
        """
        print("\n" + "="*50)
        print("Starting Block J Post-Processing (Calculations)")
        print("="*50)
        
        result = self.fill_calculated_fields()
        
        print("\n" + "="*50)
        print("Block J Post-Processing Complete")
        print("="*50 + "\n")
        
        return result


# Example usage
if __name__ == "__main__":
    # Example data
    block_j = {
        "Block J: Products and by-products manufactured by the unit": {
            "1. Product 1": {
                "Item description": "Product A",
                "Item code (NPCMS)": "12345",
                "Unit of quantity": "Kg",
                "Quantity manufactured": "1000",
                "Quantity sold": "950",
                "Gross sale value (Rs.)": "100000",
                "Distributive expenses (Rs.)": {
                    "Goods and Services Tax(GST)": "18000",
                    "Excise Duty/Sales Tax/VAT/Other Taxes, if any": "5000",
                    "Other Distributive Expenses": "2000",
                    "Subsidy (-)": "0"
                },
                "Per unit net sale value (Rs. 0.00)": "",
                "Ex-factory value of quantity manufactured (Rs.)": ""
            },
            "2. Product 2": {
                "Item description": "Product B",
                "Item code (NPCMS)": "12346",
                "Unit of quantity": "Litre",
                "Quantity manufactured": "500",
                "Quantity sold": "480",
                "Gross sale value (Rs.)": "50000",
                "Distributive expenses (Rs.)": {
                    "Goods and Services Tax(GST)": "9000",
                    "Excise Duty/Sales Tax/VAT/Other Taxes, if any": "2000",
                    "Other Distributive Expenses": "1000",
                    "Subsidy (-)": "500"
                },
                "Per unit net sale value (Rs. 0.00)": "",
                "Ex-factory value of quantity manufactured (Rs.)": ""
            },
            "12. Total (items 1 to 11)": {
                "Item description": "Total",
                "Item code (NPCMS)": "9995000",
                "Unit of quantity": "",
                "Quantity manufactured": "",
                "Quantity sold": "",
                "Gross sale value (Rs.)": "",
                "Distributive expenses (Rs.)": {
                    "Goods and Services Tax(GST)": "",
                    "Excise Duty/Sales Tax/VAT/Other Taxes, if any": "",
                    "Other Distributive Expenses": "",
                    "Subsidy (-)": ""
                },
                "Per unit net sale value (Rs. 0.00)": "",
                "Ex-factory value of quantity manufactured (Rs.)": ""
            }
        }
    }
    
    # Process
    processor = BlockJJsonProcessor(block_j_json=block_j)
    result = processor.process()
    
    print("\nFinal Block J JSON:")
    print(json.dumps(result, indent=2))