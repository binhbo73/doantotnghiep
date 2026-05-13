import torch
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        total = torch.cuda.get_device_properties(i).total_memory
        print(f"    VRAM: {total / 1024**3:.1f} GB")
else:
    print("  No GPU detected")
import psutil
mem = psutil.virtual_memory()
print(f"RAM total: {mem.total / 1024**3:.1f} GB")
print(f"RAM free: {mem.available / 1024**3:.1f} GB")
