import json
nb = json.load(open('D:/DBSCodingCamp/qlop/ai_engine/notebooks/qlop-ner-cv-extraction.ipynb', encoding='utf-8'))
cells_of_interest = {4: "CFG", 7: "data_loading", 17: "ITHead", 22: "Loss", 25: "Optimizer"}
for idx, name in cells_of_interest.items():
    src = ''.join(nb['cells'][idx]['source'])
    safe = src.encode('ascii','replace').decode()
    print(f"\n=== Cell {idx} ({name}) ===")
    print(safe[:2000])
