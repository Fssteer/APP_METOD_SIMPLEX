#!/bin/bash
echo "=== Iniciando Frontend (Reflex) ==="
cd frontend
pip install -r requirements.txt -q
reflex run
