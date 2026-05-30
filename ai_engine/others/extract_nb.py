import json

with open('ai_engine/notebooks/capstone-dbs-intelligent-recommendation.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
print(f'Total cells: {len(cells)}')
for i, c in enumerate(cells):
    src = ''.join(c['source'])
    keywords = ['def build_model', 'Sequential', 'Dense', 'model.compile', 'model.fit',
                'saved_model', 'tf.saved_model', 'Embedding', 'concatenate', 'Model(']
    if any(kw in src for kw in keywords):
        print(f'--- Cell {i} ({c["cell_type"]}) ---')
        print(src[:3000])
        print()
