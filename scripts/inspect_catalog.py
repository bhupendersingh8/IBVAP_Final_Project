import yaml
import json

with open('ml/registry/model_registry.yaml', encoding='utf-8') as f:
    data = yaml.safe_load(f)

models = data.get('models', [])
print(f"Total models in registry: {len(models)}")

pool_counts = {}
for m in models:
    pool = m.get('expert_pool', 'unknown')
    pool_counts[pool] = pool_counts.get(pool, 0) + 1

for p, c in sorted(pool_counts.items()):
    print(f"- {p}: {c} models")
