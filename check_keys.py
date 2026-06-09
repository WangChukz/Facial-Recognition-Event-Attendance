import numpy as np
data = np.load(r'backend/training/scenario_embeddings_cache.npz')
print('Available keys:', list(data.keys()))
for key in data.keys():
    print(f"  {key}: shape {data[key].shape}")
