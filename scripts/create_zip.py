import os
import zipfile

def create_zip():
    zip_filename = 'IBVAP_Project.zip'
    exclude_dirs = {'.git', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache', 'infrastructure\\mediamtx'}
    exclude_files = {zip_filename, 'yolov8n.pt'}

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not any(ex in os.path.join(root, d) for ex in exclude_dirs)]
            
            for file in files:
                if file in exclude_files or file.endswith('.zip') or file.endswith('.pt'):
                    continue
                file_path = os.path.join(root, file)
                # Ensure we don't zip the zip itself
                if file_path.endswith(zip_filename):
                    continue
                zipf.write(file_path, arcname=os.path.relpath(file_path, '.'))
    print(f"Successfully created {zip_filename}")

if __name__ == '__main__':
    create_zip()
