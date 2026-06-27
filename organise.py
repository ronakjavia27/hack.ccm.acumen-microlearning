import os
import shutil
import re
import pandas as pd

# --- CONFIGURATION ---
EXCEL_FILE = "sent_summaries.xlsx"
SOURCE_DIR = "output_files"
TARGET_DIR = "output_file"  # As requested: /output_file/[system_name]/[type]

def sanitize_folder_name(name):
    """Removes trailing spaces, forces title casing, and strips illegal characters."""
    if pd.isna(name) or str(name).strip() == "":
        return "Uncategorized"
    clean = str(name).strip().title()
    return re.sub(r'[\\/*?:"<>|]', "", clean)

def organize_json_files():
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: Could not find '{EXCEL_FILE}' in the root directory.")
        return

    print("📊 Reading Excel ledger entries...")
    # Read columns: B (Index 1: File Name), G (Index 6: System), H (Index 7: Article Type)
    try:
        df = pd.read_excel(EXCEL_FILE, usecols=[1, 6, 7], header=None)
    except Exception as e:
        print(f"❌ Failed to parse Excel sheet: {e}")
        return

    success_count = 0
    missing_count = 0

    # Iterate through rows starting from index 0 or headers if present
    for index, row in df.iterrows():
        excel_filename = row.iloc[0]
        system_raw = row.iloc[1]
        type_raw = row.iloc[2]

        # Skip empty rows or header baseline titles
        if pd.isna(excel_filename) or str(excel_filename).lower() in ["file name", "filename"]:
            continue

        # Convert the ledger filename from .pdf to .json matching pattern
        pdf_name = str(excel_filename).strip()
        json_name = os.path.splitext(pdf_name)[0] + ".json"
        
        source_file_path = os.path.join(SOURCE_DIR, json_name)

        # Check if the generated JSON file actually exists in output_files
        if os.path.exists(source_file_path):
            # Format clean path metrics
            system_dir = sanitize_folder_name(system_raw)
            type_dir = sanitize_folder_name(type_raw)
            
            # Construct destination: /output_file/[system_name]/[article_or_guidelines]
            destination_dir = os.path.join(TARGET_DIR, system_dir, type_dir)
            os.makedirs(destination_dir, exist_ok=True)
            
            destination_file_path = os.path.join(destination_dir, json_name)
            
            # Safely migrate payload block
            try:
                shutil.move(source_file_path, destination_file_path)
                print(f"✅ Moved: {json_name} ➔ {system_dir}/{type_dir}/")
                success_count += 1
            except Exception as move_err:
                print(f"⚠️ Failed to move {json_name}: {move_err}")
        else:
            # File might have already been processed/moved or doesn't exist yet
            missing_count += 1

    print("\n--- Execution Summary ---")
    print(f"📦 Successfully categorized & moved: {success_count} JSON file(s)")
    print(f"🔍 Entries not found in '{SOURCE_DIR}' layout: {missing_count} (Likely already moved or processing pending)")

if __name__ == "__main__":
    organize_json_files()