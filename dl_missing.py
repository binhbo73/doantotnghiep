import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import hf_hub_download

local_dir = "./models/bge-m3-hfmirror"

# Missing files to download
missing = [
    "sparse_linear.pt",
    "configuration.json",
]

for fname in missing:
    print(f"Downloading {fname}...")
    try:
        path = hf_hub_download("BAAI/bge-m3", fname, local_dir=local_dir)
        print(f"  OK: {fname}")
    except Exception as e:
        print(f"  FAILED: {e}")

print("Done!")
