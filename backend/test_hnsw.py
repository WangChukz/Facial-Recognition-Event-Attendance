import os
import sys
import time
import tempfile
import uuid
from typing import Any

import numpy as np

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.faiss_indexer import FaissFaceIndex
from app.services.faiss_indexer_hnsw import HNSWFaceIndex


def generate_fake_embeddings(num_users: int = 100, embeddings_per_user: int = 18, dim: int = 512):
    """
    Generate fake face embeddings for testing.
    
    Returns:
        users: dict[user_uuid] -> list[embeddings]
        all_embeddings: list[(embedding, user_uuid)]
    """
    np.random.seed(42)
    users = {}
    all_embeddings = []
    
    for user_idx in range(num_users):
        user_id = uuid.uuid4()
        user_embeddings = []
        
        # Generate base embedding for this user
        base_embedding = np.random.randn(dim).astype(np.float32)
        base_embedding /= np.linalg.norm(base_embedding)
        
        # Generate 18 embeddings per user with small noise
        for emb_idx in range(embeddings_per_user):
            noise = np.random.randn(dim).astype(np.float32) * 0.05  # Small noise
            embedding = base_embedding + noise
            embedding /= np.linalg.norm(embedding)  # Normalize
            
            user_embeddings.append(embedding)
            all_embeddings.append((embedding.copy(), user_id))
        
        users[user_id] = user_embeddings
    
    return users, all_embeddings


def populate_index(index, all_embeddings):
    """Add all embeddings to index."""
    faiss_id = 0
    for embedding, user_id in all_embeddings:
        embedding_uuid = uuid.uuid4()
        index.add_with_id(embedding, faiss_id, embedding_uuid, user_id)
        faiss_id += 1


def run_benchmark():
    """Run benchmark comparing FaissFaceIndex vs HNSWFaceIndex."""
    
    print("=" * 80)
    print("BENCHMARK: FaissFaceIndex (Flat) vs HNSWFaceIndex (HNSW)")
    print("=" * 80)
    
    # Generate fake data
    print("\n[1] Generating fake data...")
    num_users = 100
    embeddings_per_user = 18
    total_embeddings = num_users * embeddings_per_user
    
    users, all_embeddings = generate_fake_embeddings(num_users, embeddings_per_user)
    print(f"    ✓ Generated {num_users} users, {embeddings_per_user} embeddings per user = {total_embeddings} total")
    
    # Create temporary directories for indexes
    with tempfile.TemporaryDirectory() as tmpdir:
        flat_index_path = os.path.join(tmpdir, "flat_index.faiss")
        flat_meta_path = os.path.join(tmpdir, "flat_meta.json")
        
        hnsw_index_path = os.path.join(tmpdir, "hnsw_index.faiss")
        hnsw_meta_path = os.path.join(tmpdir, "hnsw_meta.json")
        
        # Create and populate indexes
        print("\n[2] Creating and populating indexes...")
        
        flat_index = FaissFaceIndex(flat_index_path, flat_meta_path)
        hnsw_index = HNSWFaceIndex(hnsw_index_path, hnsw_meta_path)
        
        # Populate FaissFaceIndex
        start_time = time.time()
        populate_index(flat_index, all_embeddings)
        flat_populate_time = time.time() - start_time
        print(f"    ✓ FaissFaceIndex populated in {flat_populate_time:.3f}s")
        
        # Populate HNSWFaceIndex
        start_time = time.time()
        populate_index(hnsw_index, all_embeddings)
        hnsw_populate_time = time.time() - start_time
        print(f"    ✓ HNSWFaceIndex populated in {hnsw_populate_time:.3f}s")
        
        # Persist indexes
        flat_index.persist()
        hnsw_index.persist()
        
        print(f"    ✓ FaissFaceIndex total: {flat_index.total}")
        print(f"    ✓ HNSWFaceIndex total: {hnsw_index.total}")
        
        # Run benchmark queries
        print("\n[3] Running 50 benchmark queries...")
        num_queries = 50
        top_k = 3
        
        query_user_ids = np.random.choice(list(users.keys()), num_queries, replace=True)
        
        flat_search_times = []
        hnsw_search_times = []
        flat_recalls = []
        hnsw_recalls = []
        
        query_results = []
        
        for query_idx in range(num_queries):
            query_user_id = query_user_ids[query_idx]
            base_embedding = users[query_user_id][0]
            
            # Add small noise to query embedding
            noise = np.random.randn(512).astype(np.float32) * 0.03
            query_embedding = base_embedding + noise
            query_embedding /= np.linalg.norm(query_embedding)
            
            # Search Flat index
            start_time = time.time()
            flat_results = flat_index.search(query_embedding, top_k=top_k)
            flat_time = (time.time() - start_time) * 1000  # Convert to ms
            flat_search_times.append(flat_time)
            
            # Search HNSW index
            start_time = time.time()
            hnsw_results = hnsw_index.search(query_embedding, top_k=top_k)
            hnsw_time = (time.time() - start_time) * 1000  # Convert to ms
            hnsw_search_times.append(hnsw_time)
            
            # Calculate recall (did we find the correct user in top-k results?)
            flat_found = any(res["user_id"] == str(query_user_id) for res in flat_results)
            hnsw_found = any(res["user_id"] == str(query_user_id) for res in hnsw_results)
            
            flat_recalls.append(1 if flat_found else 0)
            hnsw_recalls.append(1 if hnsw_found else 0)
            
            # Store detailed results
            query_results.append({
                "query_idx": query_idx,
                "query_user_id": str(query_user_id)[:8],
                "flat_results": flat_results,
                "hnsw_results": hnsw_results,
                "flat_found": flat_found,
                "hnsw_found": hnsw_found,
            })
        
        # Calculate statistics
        print(f"    ✓ Completed {num_queries} queries")
        
        flat_avg_time = np.mean(flat_search_times)
        hnsw_avg_time = np.mean(hnsw_search_times)
        
        flat_recall = np.mean(flat_recalls) * 100
        hnsw_recall = np.mean(hnsw_recalls) * 100
        
        # Print summary table
        print("\n" + "=" * 80)
        print("SUMMARY COMPARISON")
        print("=" * 80)
        print(f"{'Metric':<30} | {'FaissFaceIndex':<20} | {'HNSWFaceIndex':<20}")
        print("-" * 80)
        print(f"{'Avg Search Time (ms)':<30} | {flat_avg_time:<20.4f} | {hnsw_avg_time:<20.4f}")
        print(f"{'Recall @ top-3 (%)':<30} | {flat_recall:<20.1f} | {hnsw_recall:<20.1f}")
        print(f"{'Total Vectors':<30} | {flat_index.total:<20} | {hnsw_index.total:<20}")
        print("=" * 80)
        
        # Print detailed query results
        print("\n" + "=" * 80)
        print("DETAILED QUERY RESULTS (Top-3)")
        print("=" * 80)
        
        for result in query_results:
            print(f"\nQuery {result['query_idx']:2d} (User: {result['query_user_id']})")
            print("-" * 80)
            
            # FaissFaceIndex results
            print("  FaissFaceIndex:")
            if result["flat_results"]:
                for i, res in enumerate(result["flat_results"], 1):
                    match = "✓" if res["user_id"] == result["query_user_id"] else " "
                    print(f"    {i}. [ID: {res['faiss_id']:3d}] {match} sim={res['similarity']:.4f} "
                          f"user={res['user_id'][:8]}")
            else:
                print("    (no results)")
            
            # HNSWFaceIndex results
            print("  HNSWFaceIndex:")
            if result["hnsw_results"]:
                for i, res in enumerate(result["hnsw_results"], 1):
                    match = "✓" if res["user_id"] == result["query_user_id"] else " "
                    print(f"    {i}. [ID: {res['faiss_id']:3d}] {match} sim={res['similarity']:.4f} "
                          f"user={res['user_id'][:8]}")
            else:
                print("    (no results)")


if __name__ == "__main__":
    run_benchmark()
