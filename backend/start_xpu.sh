#!/bin/bash
# Inicia o backend MedAssist com suporte a Intel Arc XPU
# Resolve conflito de libstdc++ entre anaconda e sistema

export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6
export LD_LIBRARY_PATH=${CONDA_PREFIX:-$HOME/anaconda3}/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export ZE_ENABLE_SYSMAN=1
export ONEAPI_DEVICE_SELECTOR="level_zero:0"

echo "=== MedAssist Backend com Intel XPU ==="
python -c "
import torch
if torch.xpu.is_available():
    print(f'  GPU: {torch.xpu.get_device_name(0)}')
    print(f'  VRAM: {torch.xpu.get_device_properties(0).total_memory / 1024**3:.1f} GB')
else:
    print('  AVISO: XPU não disponível, usando CPU')
"
echo "========================================"

exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
