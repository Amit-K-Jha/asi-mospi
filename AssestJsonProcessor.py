import json
import copy

class AssetJsonProcessor:
    def __init__(self, filled_json, blank_json):
        self.filled_json = self.wrap_filled_json(filled_json)
        self.blank_json = copy.deepcopy(blank_json)
        self.result_json = copy.deepcopy(blank_json)
    
    @staticmethod
    def safe_float(value):
        """Safely converts a value to float, returning 0 if it's not a valid number."""
        try:
            return float(value) if value not in ["", None] else 0.0
        except:
            return 0.0

    @staticmethod
    def wrap_filled_json(filled_json):
        """Wrap the filled JSON into the 'Type of Assets' structure."""
        return {
            "Type of Assets": filled_json
        }

    def fill_blank_json(self):
        asset_data = self.result_json.get("Type of Assets", {})

        # Step 1: Fill missing values from filled_json
        for asset_key in asset_data:
            if asset_key in self.filled_json["Type of Assets"]:
                for section in asset_data[asset_key]:
                    for field in asset_data[asset_key][section]:
                        asset_data[asset_key][section][field] = self.filled_json["Type of Assets"][asset_key][section].get(field, "")

        # Step 2: Compute Sub-total (items 2 to 7)
        subtotal_key = "8. Sub-total (items 2 to 7)"
        asset_data[subtotal_key] = {}
        first_asset = next(iter(asset_data))  # To iterate over sections

        for section in asset_data[first_asset]:
            asset_data[subtotal_key][section] = {}
            for field in asset_data[first_asset][section]:
                subtotal = 0.0
                for i in range(2, 8):
                    prefix = f"{i}."
                    match_key = next((k for k in asset_data if k.startswith(prefix)), None)
                    if match_key:
                        val = asset_data[match_key][section].get(field, 0)
                        if isinstance(val, dict):
                            continue
                        subtotal += self.safe_float(val)
                asset_data[subtotal_key][section][field] = str(round(subtotal, 2))

        # Step 3: Compute Total (items 1 + 8 + 9)
        total_key = "10. Total (items 1+8+9)"
        asset_data[total_key] = {}
        for section in asset_data[first_asset]:
            asset_data[total_key][section] = {}
            for field in asset_data[first_asset][section]:
                total = 0.0
                for i in [1, 8, 9]:
                    prefix = f"{i}."
                    match_key = next((k for k in asset_data if k.startswith(prefix)), None)
                    if match_key:
                        val = asset_data[match_key][section].get(field, 0)
                        if isinstance(val, dict):
                            continue
                        total += self.safe_float(val)

                sub_val = asset_data[subtotal_key][section].get(field, 0)
                if isinstance(sub_val, dict):
                    continue
                total += self.safe_float(sub_val)

                asset_data[total_key][section][field] = str(round(total, 2))

        self.result_json["Type of Assets"] = asset_data
        return self.result_json
