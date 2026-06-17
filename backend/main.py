from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import math

app = FastAPI(title="Simplex API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SimplexInput(BaseModel):
    objetivo: List[float]
    restricciones: List[List[float]]
    rhs: List[float]

class Iteracion(BaseModel):
    numero: int
    descripcion: str
    nota_pivote: Optional[str]
    columna_pivote: Optional[int]
    fila_pivote: Optional[int]
    base: List[str]
    nombres_columnas: List[str]
    tabla: List[List[float]]

class SimplexOutput(BaseModel):
    exito: bool
    mensaje: str
    iteraciones: List[Iteracion]
    z_optimo: Optional[float]
    variables_decision: Optional[List[float]]
    holguras: Optional[List[float]]
    nombres_variables: Optional[List[str]]

def redondear(v: float) -> float:
    r = round(v, 8)
    return 0.0 if abs(r) < 1e-9 else r

def snap(tableau, basis, col_names, nc, num, desc, nota, piv_col, piv_row) -> Iteracion:
    return Iteracion(
        numero=num,
        descripcion=desc,
        nota_pivote=nota,
        columna_pivote=piv_col,
        fila_pivote=piv_row,
        base=[col_names[b] for b in basis],
        nombres_columnas=col_names,
        tabla=[[redondear(v) for v in row] for row in tableau],
    )

def resolver_simplex(obj, A, b) -> SimplexOutput:
    nv = len(obj)
    nc = len(A)

    if any(rhs < 0 for rhs in b):
        return SimplexOutput(exito=False, mensaje="RHS no puede ser negativo.",
                             iteraciones=[], z_optimo=None, variables_decision=None,
                             holguras=None, nombres_variables=None)

    total = nv + nc
    col_names = [f"x{i+1}" for i in range(nv)] + [f"S{i+1}" for i in range(nc)] + ["R"]

    # Construir tableau inicial
    tableau = []
    tableau.append([-c for c in obj] + [0.0]*nc + [0.0])
    for i in range(nc):
        tableau.append(list(A[i]) + [1.0 if j==i else 0.0 for j in range(nc)] + [b[i]])

    basis = list(range(nv, nv+nc))
    iteraciones = []
    iter_num = 0

    # ── Tabla inicial ──────────────────────────────────────────────────────
    iteraciones.append(snap(tableau, basis, col_names, nc, iter_num,
        "Tabla inicial — variables básicas son las holguras", None, None, None))

    MAX_ITER = 50
    while iter_num < MAX_ITER:

        # ── Buscar columna pivote (más negativo en Z) ──────────────────────
        piv_col = -1
        min_val = -1e-9
        for j in range(total):
            if tableau[0][j] < min_val:
                min_val = tableau[0][j]
                piv_col = j

        if piv_col == -1:
            break  # óptimo

        # ── Buscar fila pivote (ratio mínimo) ──────────────────────────────
        piv_row = -1
        min_ratio = math.inf
        ratios = []
        for i in range(1, nc+1):
            if tableau[i][piv_col] > 1e-9:
                r = tableau[i][total] / tableau[i][piv_col]
                ratios.append(f"R{i}: {redondear(r):.4g}")
                if r < min_ratio:
                    min_ratio = r
                    piv_row = i
            else:
                ratios.append(f"R{i}: ∞")

        if piv_row == -1:
            return SimplexOutput(exito=False, mensaje="Problema no acotado.",
                                 iteraciones=iteraciones, z_optimo=None,
                                 variables_decision=None, holguras=None, nombres_variables=None)

        iter_num += 1
        var_entra = col_names[piv_col]
        var_sale  = col_names[basis[piv_row-1]]
        piv_val   = redondear(tableau[piv_row][piv_col])

        # ── Paso A: mostrar tabla con pivote identificado ──────────────────
        nota_a = (f"Columna entrante: {var_entra} (más negativo en Z = {redondear(min_val)}) | "
                  f"Ratios: {', '.join(ratios)} | "
                  f"Fila saliente: {var_sale} (ratio mínimo = {redondear(min_ratio):.4g}) | "
                  f"Elemento pivote: {piv_val}")
        iteraciones.append(snap(tableau, basis, col_names, nc, iter_num,
            f"Iteración {iter_num} — Paso A: Identificar pivote "
            f"(entra {var_entra}, sale {var_sale})",
            nota_a, piv_col, piv_row))

        # ── Actualizar base ────────────────────────────────────────────────
        basis[piv_row-1] = piv_col

        # ── Paso B: normalizar fila pivote (dividir entre elemento pivote) ─
        piv_elem = tableau[piv_row][piv_col]
        for j in range(total+1):
            tableau[piv_row][j] /= piv_elem

        nota_b = (f"Paso B: Normalizar fila {piv_row} (÷ {piv_val}) "
                  f"→ convertir elemento pivote en 1")
        iteraciones.append(snap(tableau, basis, col_names, nc, iter_num,
            f"Iteración {iter_num} — Paso B: Normalizar fila pivote ÷ {piv_val}",
            nota_b, piv_col, piv_row))

        # ── Paso C: eliminar en cada otra fila ─────────────────────────────
        for i in range(nc+1):
            if i == piv_row:
                continue
            factor = redondear(tableau[i][piv_col])
            if abs(factor) < 1e-12:
                continue
            for j in range(total+1):
                tableau[i][j] -= factor * tableau[piv_row][j]

            fila_nom = "Z" if i == 0 else col_names[basis[i-1]]
            signo = "-" if factor > 0 else "+"
            nota_c = (f"Paso C: Hacer cero columna {var_entra} en fila {fila_nom} "
                      f"→ ({signo}{abs(factor):.4g}) × F{piv_row} + F{i if i>0 else 'Z'}")
            iteraciones.append(snap(tableau, basis, col_names, nc, iter_num,
                f"Iteración {iter_num} — Paso C: Cero en fila {fila_nom} "
                f"(col {var_entra})",
                nota_c, piv_col, None))

    # ── Tabla óptima ──────────────────────────────────────────────────────
    iteraciones[-1].descripcion = "✓ Tabla óptima — No quedan coeficientes negativos en Z"

    sol = [0.0] * total
    for k in range(nc):
        sol[basis[k]] = tableau[k+1][total]

    z_opt     = redondear(tableau[0][total])
    vars_dec  = [redondear(sol[j]) for j in range(nv)]
    holguras  = [redondear(sol[nv+j]) for j in range(nc)]

    return SimplexOutput(
        exito=True,
        mensaje=f"Solución óptima encontrada en {iter_num} iteración(es).",
        iteraciones=iteraciones,
        z_optimo=z_opt,
        variables_decision=vars_dec,
        holguras=holguras,
        nombres_variables=[f"x{j+1}" for j in range(nv)],
    )

@app.post("/simplex", response_model=SimplexOutput)
def simplex(data: SimplexInput):
    return resolver_simplex(data.objetivo, data.restricciones, data.rhs)

@app.get("/ejemplo")
def ejemplo():
    return {"objetivo":[50,80],"restricciones":[[1,2],[1,1]],"rhs":[120,90]}

@app.get("/health")
def health():
    return {"status":"ok"}
