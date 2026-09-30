from pathlib import Path

def create_clean_zip():
    source_dir = str(Path(__file__).resolve().parent.parent)
    target_zip = str(Path(__file__).resolve().parent.parent.parent / "IBVAP_Export" / "IBVAP_Final_Project.zip")
    
    # Exclude non-transferable folders
    exclude_dirs = {'.git', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache'}
    
    # Make sure target directory exists
    os.makedirs(os.path.dirname(target_zip), exist_ok=True)
    
    print(f"Creating pristine zip at {target_zip}...")
    
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude folders
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not any(ex in os.path.join(root, d) for ex in exclude_dirs)]
            
            for file in files:
                if file.endswith('.zip'):
                    continue  # Just in case, exclude any other zips
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname=arcname)
                
    print(f"Successfully packaged the project into: {target_zip}")

if __name__ == '__main__':
    create_clean_zip()
