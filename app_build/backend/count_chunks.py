import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from app.services.rag_service import dual_rag_pipeline as rp
m = rp.retriever.retriever.manager
base = m.base_dir

for sub in ['legal_knowledge', 'case_examples']:
    sub_dir = os.path.join(base, sub)
    print(f'\n=== {sub} ===')
    for fname in sorted(os.listdir(sub_dir)):
        if fname.endswith('_meta.json'):
            path = os.path.join(sub_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            print(f'  {fname}: {len(meta)} chunks')
            if meta:
                first = meta[0]
                text = first.get('text', first.get('content', str(first)[:200]))
                sample = text[:120].encode('ascii', 'replace').decode('ascii')
                print(f'    Sample: {sample}')
