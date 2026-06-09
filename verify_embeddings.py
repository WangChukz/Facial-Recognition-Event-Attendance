import numpy as np
import json

# Verify network embeddings
emb = np.load('backend/training/network_embeddings.npy')
print(f'[OK] Embeddings shape: {emb.shape}')

with open('backend/training/network_embeddings_metadata.json') as f:
    meta = json.load(f)
    print(f'[OK] Metadata total: {meta["total"]}')
    print(f'[OK] Embedding dim: {meta["embedding_dim"]}')
    print(f'[OK] Samples collected: {len(meta["samples"])}')
