# Simplex IO — App Android (Flet)
**Universidad de Panamá · Investigación de Operaciones**

---

## Estructura

```
simplex_flet/
├── main.py                          # App Flet completa
├── requirements.txt                 # flet + httpx
├── assets/
│   └── UP-logo.png                  # Logo UP
└── .github/
    └── workflows/
        └── build-apk.yml            # GitHub Actions → genera .apk
```

---

## Paso 1 — Configurar la IP del backend

En `main.py` línea 7, cambia:
```python
BACKEND_URL = "http://TU_IP:8080"
```
Por la IP local de tu Mac donde corre FastAPI:
```python
BACKEND_URL = "http://192.168.1.X:8080"  # tu IP real
```

Para saber tu IP en Mac:
```bash
ipconfig getifaddr en0
```

El backend FastAPI debe correr en:
```bash
cd simplex_project/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```
> ⚠️ `--host 0.0.0.0` es importante para que el celular pueda conectarse.

---

## Paso 2 — Subir a GitHub y generar el APK

```bash
cd simplex_flet

# Inicializar repo
git init
git add .
git commit -m "Initial commit - Simplex Flet app"

# Crear repo en github.com, luego:
git remote add origin https://github.com/TU_USUARIO/simplex-flet.git
git branch -M main
git push -u origin main
```

GitHub Actions arranca automáticamente.

---

## Paso 3 — Descargar el APK

1. Ve a tu repo en GitHub
2. Click en **Actions**
3. Click en el workflow **Build Android APK**
4. Al terminar (≈ 10-15 min), click en **simplex-apk** bajo **Artifacts**
5. Descarga el `.zip`, extrae el `.apk`
6. Pásalo al celular e instala (habilita "Fuentes desconocidas")

---

## Prueba local (sin compilar APK)

```bash
cd simplex_flet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Se abre en el navegador en `http://localhost:8550`
