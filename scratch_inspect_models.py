import torch
import sys
from pathlib import Path

def inspect_model(path_str):
    p = Path(path_str)
    if not p.exists():
        return 'NOT FOUND'
    try:
        data = torch.load(p, map_location='cpu', weights_only=False)
        
        info = []
        if isinstance(data, dict):
            if 'model' in data:
                model = data['model']
                info.append(f"Model Class: {model.__class__.__name__}")
                info.append(f"Yaml: {getattr(model, 'yaml', {}).get('yaml_file', getattr(model, 'yaml', {}))}")
                
                # count parameters
                params = sum(p.numel() for p in model.parameters() if p.requires_grad)
                info.append(f"Params: {params}")
            if 'date' in data:
                info.append(f"Date: {data['date']}")
            if 'version' in data:
                info.append(f"Ultralytics Version: {data['version']}")
            if 'task' in data:
                info.append(f"Task: {data['task']}")
            if 'epoch' in data:
                info.append(f"Epoch: {data['epoch']}")
        elif hasattr(data, 'state_dict'):
             info.append("Type: Torch Module")
        else:
             info.append(f"Type: {type(data)}")
        return ' | '.join(info)
    except Exception as e:
        return f"Error: {e}"

for model_file in ['weights/yolo26x.pt', 'weights/yolo26n.pt', 'weights/yolo11n.pt']:
    print(f"--- {model_file} ---")
    print(inspect_model(model_file))

