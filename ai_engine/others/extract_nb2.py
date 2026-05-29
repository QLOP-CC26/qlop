import json, sys

with open('ai_engine/notebooks/capstone-dbs-intelligent-learning-recommendation.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
print(f'Total cells: {len(cells)}')
for i, c in enumerate(cells):
    src = ''.join(c['source'])
    keywords = ['TwoTower', 'build_model', 'N_SKILLS', 'N_SKILLS_CR', 'course_tower',
                'demand_tower', 'saved_model', 'serving_default', 'output_0', 'args_0']
    if any(kw in src for kw in keywords):
        print(f'--- Cell {i} ({c["cell_type"]}) ---')
        print(src[:3000].encode('ascii', 'replace').decode())
        print()
