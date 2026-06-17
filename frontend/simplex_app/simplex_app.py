import reflex as rx
import httpx
from typing import List

BACKEND_URL = "http://localhost:8080"

# ── Paleta ────────────────────────────────────────────────────────────────────
RED      = "#C0392B"
RED_D    = "#7B241C"
RED_L    = "#E74C3C"
RED_G    = "rgba(192,57,43,0.18)"
RED_G2   = "rgba(192,57,43,0.08)"
GOLD     = "#F1C40F"
GOLD_D   = "#D4AC0D"
GOLD_G   = "rgba(241,196,15,0.14)"
GOLD_G2  = "rgba(241,196,15,0.06)"
BLUE     = "#2471A3"
BLUE_L   = "#3498DB"
BLUE_G   = "rgba(36,113,163,0.18)"
BLUE_H   = "rgba(36,113,163,0.32)"
GREEN    = "#1E8449"
GREEN_L  = "#27AE60"
GREEN_G  = "rgba(30,132,73,0.14)"
ORANGE   = "#D35400"
ORANGE_G = "rgba(211,84,0,0.14)"
PURPLE   = "#7D3C98"
PURPLE_G = "rgba(125,60,152,0.14)"
BG       = "#070a10"
BG2      = "#0d1119"
BG3      = "#131824"
BG4      = "#191f2e"
BG5      = "#1e2538"
BORDER   = "#1e2840"
BORDER2  = "#2d3a55"
TXT      = "#dde3f0"
TXT2     = "#7a89a8"
TXT3     = "#3d4d6a"
NEG      = "#F1948A"

def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9: return str(int(round(v)))
    for d in range(1, 33):
        n = round(v * d)
        if abs(n / d - v) < 1e-9: return f"{n}/{d}"
    return f"{v:.4f}"

# ── State ─────────────────────────────────────────────────────────────────────
class SimplexState(rx.State):
    n_vars: int = 2
    n_cons: int = 2
    obj:  List[str] = ["50","80","",""]
    cons: List[str] = ["1","2","","","1","1","","","","","","","","","",""]
    rhs:  List[str] = ["120","90","",""]

    loading:            bool        = False
    error_msg:          str         = ""
    resuelto:           bool        = False
    z_optimo:           float       = 0.0
    variables_decision: List[float] = []
    holguras:           List[float] = []
    mensaje:            str         = ""

    iter_descripciones: List[str] = []
    iter_notas:         List[str] = []
    iter_piv_col:       List[int] = []
    iter_piv_row:       List[int] = []
    iter_col_names:     List[str] = []
    iter_base:          List[str] = []
    iter_tabla:         List[str] = []
    iter_activa:        int       = 0
    total_iters:        int       = 0

    tabla_activa_filas:   List[List[str]] = []
    tabla_activa_cols:    List[str]       = []
    tabla_activa_base:    List[str]       = []
    tabla_activa_piv_col: int             = -1
    tabla_activa_piv_row: int             = -1
    tabla_activa_desc:    str             = ""
    tabla_activa_nota:    str             = ""

    def _reset(self):
        self.resuelto=False; self.z_optimo=0.0
        self.variables_decision=[]; self.holguras=[]
        self.mensaje=""; self.error_msg=""
        self.iter_descripciones=[]; self.iter_notas=[]
        self.iter_piv_col=[]; self.iter_piv_row=[]
        self.iter_col_names=[]; self.iter_base=[]
        self.iter_tabla=[]; self.iter_activa=0; self.total_iters=0
        self.tabla_activa_filas=[]; self.tabla_activa_cols=[]
        self.tabla_activa_base=[]; self.tabla_activa_piv_col=-1
        self.tabla_activa_piv_row=-1; self.tabla_activa_desc=""
        self.tabla_activa_nota=""

    def set_n_vars(self, v: str): self.n_vars=int(v); self._reset()
    def set_n_cons(self, v: str): self.n_cons=int(v); self._reset()
    def set_obj(self, idx: int, v: str):  self.obj[idx]=v
    def set_cons(self, idx: int, v: str): self.cons[idx]=v
    def set_rhs(self, idx: int, v: str):  self.rhs[idx]=v

    def cargar_ejemplo(self):
        self.n_vars=2; self.n_cons=2
        self.obj=["50","80","",""]
        self.cons=["1","2","","","1","1","","","","","","","","","",""]
        self.rhs=["120","90","",""]
        self._reset()

    def limpiar(self): self._reset()

    def _decode_iter(self, idx: int):
        self.tabla_activa_cols=self.iter_col_names[idx].split("|")
        self.tabla_activa_base=self.iter_base[idx].split("|")
        self.tabla_activa_piv_col=self.iter_piv_col[idx]
        self.tabla_activa_piv_row=self.iter_piv_row[idx]
        self.tabla_activa_desc=self.iter_descripciones[idx]
        self.tabla_activa_nota=self.iter_notas[idx]
        self.tabla_activa_filas=[r.split("|") for r in self.iter_tabla[idx].split(";")]

    def set_iter(self, i: int):
        self.iter_activa=i; self._decode_iter(i)

    def prev_iter(self):
        if self.iter_activa > 0:
            self.iter_activa -= 1; self._decode_iter(self.iter_activa)

    def next_iter(self):
        if self.iter_activa < self.total_iters - 1:
            self.iter_activa += 1; self._decode_iter(self.iter_activa)

    async def resolver(self):
        self._reset(); self.loading=True; yield
        try:
            obj_vals=[]
            for j in range(self.n_vars):
                v=self.obj[j].strip()
                if not v: self.error_msg=f"Falta coeficiente en Z para x{j+1}"; self.loading=False; return
                obj_vals.append(float(v))
            A=[]
            for i in range(self.n_cons):
                row=[]
                for j in range(self.n_vars):
                    v=self.cons[i*4+j].strip()
                    if not v: self.error_msg=f"Falta coeficiente en R{i+1}, x{j+1}"; self.loading=False; return
                    row.append(float(v))
                A.append(row)
            b_vals=[]
            for i in range(self.n_cons):
                v=self.rhs[i].strip()
                if not v: self.error_msg=f"Falta RHS en restricción {i+1}"; self.loading=False; return
                b_vals.append(float(v))

            async with httpx.AsyncClient(timeout=15) as client:
                resp=await client.post(f"{BACKEND_URL}/simplex",
                    json={"objetivo":obj_vals,"restricciones":A,"rhs":b_vals})
                data=resp.json()

            if not data.get("exito"):
                self.error_msg=data.get("mensaje","Error desconocido")
            else:
                self.resuelto=True
                self.z_optimo=float(data["z_optimo"])
                self.variables_decision=[float(x) for x in data["variables_decision"]]
                self.holguras=[float(x) for x in data["holguras"]]
                self.mensaje=data["mensaje"]
                descs=[]; notas=[]; pcols=[]; prows=[]; colnames=[]; bases=[]; tablas=[]
                for it in data["iteraciones"]:
                    descs.append(it["descripcion"])
                    notas.append(it.get("nota_pivote") or "")
                    pcols.append(it["columna_pivote"] if it["columna_pivote"] is not None else -1)
                    prows.append(it["fila_pivote"] if it["fila_pivote"] is not None else -1)
                    colnames.append("|".join(it["nombres_columnas"]))
                    bases.append("|".join(it["base"]))
                    tablas.append(";".join("|".join(_fmt(v) for v in fila) for fila in it["tabla"]))
                self.iter_descripciones=descs; self.iter_notas=notas
                self.iter_piv_col=pcols; self.iter_piv_row=prows
                self.iter_col_names=colnames; self.iter_base=bases; self.iter_tabla=tablas
                self.total_iters=len(descs)
                self.iter_activa=0; self._decode_iter(0)
        except httpx.ConnectError:
            self.error_msg="No se pudo conectar al backend en localhost:8080"
        except Exception as e:
            self.error_msg=f"Error: {e}"
        finally:
            self.loading=False

# ── UI primitivos ─────────────────────────────────────────────────────────────

def glow_card(*ch, glow=RED_G, **p):
    return rx.box(*ch,
        background=f"linear-gradient(160deg, {BG3} 0%, {BG2} 100%)",
        border=f"1px solid {BORDER2}",
        border_radius="20px",
        padding="28px",
        box_shadow=f"0 0 0 1px {BORDER}, 0 8px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.03)",
        position="relative",
        overflow="hidden",
        **p)

def accent_line(color=RED):
    return rx.box(
        height="2px",
        background=f"linear-gradient(90deg, {color} 0%, transparent 100%)",
        margin_y="20px",
        border_radius="2px",
        opacity="0.6",
    )

def chip(text, color=RED, bg=RED_G2):
    return rx.box(
        rx.text(text, size="1", weight="bold", color=color,
                letter_spacing="0.07em"),
        background=bg, border=f"1px solid {color}28",
        border_radius="999px", padding="3px 12px",
        display="inline-block",
    )

def section_label(text, color=TXT2):
    return rx.hstack(
        rx.box(width="2px", height="12px",
               background=f"linear-gradient(180deg, {RED} 0%, {GOLD} 100%)",
               border_radius="2px"),
        rx.text(text, size="1", weight="bold", color=color,
                letter_spacing="0.1em", text_transform="uppercase"),
        spacing="2", align_items="center", margin_bottom="14px",
    )

def styled_input(value, on_change, w="72px"):
    return rx.input(
        value=value, on_change=on_change, type="number", width=w,
        background=BG4, color=TXT,
        border=f"1px solid {BORDER2}",
        border_radius="10px", text_align="center",
        font_size="14px", font_weight="600",
        _focus={"border_color": RED_L, "outline":"none",
                "box_shadow": f"0 0 0 3px {RED_G}, 0 0 12px {RED_G}"},
        _hover={"border_color": BORDER2, "background": BG5},
        transition="all 0.2s ease",
    )

def styled_select(choices, value, on_change, w="90px"):
    return rx.select(choices, value=value, on_change=on_change,
        background=BG4, color=TXT,
        border=f"1px solid {BORDER2}", border_radius="10px", width=w,
        _focus={"border_color": RED_L, "outline":"none"})

def lbl(t): return rx.text(t, size="2", color=TXT2, font_weight="500")

def cons_row(i: int):
    row_colors = [RED, BLUE_L, GREEN_L, GOLD_D]
    c = row_colors[i % 4]
    return rx.hstack(
        rx.box(
            rx.text(f"R{i+1}", size="1", weight="bold", color=c),
            background=f"{c}18", border=f"1px solid {c}30",
            border_radius="8px", padding="5px 10px",
            min_width="34px", text_align="center",
        ),
        styled_input(SimplexState.cons[i*4+0], lambda v,ii=i: SimplexState.set_cons(ii*4+0,v)),
        lbl("x₁"),
        rx.cond(SimplexState.n_vars>=2,
            rx.hstack(lbl("+"), styled_input(SimplexState.cons[i*4+1], lambda v,ii=i: SimplexState.set_cons(ii*4+1,v)), lbl("x₂"), spacing="2"), rx.box()),
        rx.cond(SimplexState.n_vars>=3,
            rx.hstack(lbl("+"), styled_input(SimplexState.cons[i*4+2], lambda v,ii=i: SimplexState.set_cons(ii*4+2,v)), lbl("x₃"), spacing="2"), rx.box()),
        rx.cond(SimplexState.n_vars>=4,
            rx.hstack(lbl("+"), styled_input(SimplexState.cons[i*4+3], lambda v,ii=i: SimplexState.set_cons(ii*4+3,v)), lbl("x₄"), spacing="2"), rx.box()),
        rx.text("≤", size="3", weight="bold",
                color=GOLD, style={"text_shadow": f"0 0 8px {GOLD}80"}),
        styled_input(SimplexState.rhs[i], lambda v,ii=i: SimplexState.set_rhs(ii,v)),
        spacing="2", flex_wrap="wrap", margin_bottom="10px", align_items="center",
    )

# ── Tabla Simplex ─────────────────────────────────────────────────────────────

def tabla_simplex():
    return rx.vstack(
        # Descripción del paso activo
        rx.box(
            rx.hstack(
                rx.box(
                    rx.cond(
                        SimplexState.tabla_activa_piv_col >= 0,
                        rx.icon("arrow-right-left", size=14, color=BLUE_L),
                        rx.icon("check", size=14, color=GREEN_L),
                    ),
                    background=rx.cond(
                        SimplexState.tabla_activa_piv_col >= 0,
                        BLUE_G, GREEN_G,
                    ),
                    border_radius="8px", padding="6px",
                ),
                rx.text(SimplexState.tabla_activa_desc, size="2",
                        weight="bold", color=TXT),
                spacing="3", align_items="center",
            ),
            background=BG4,
            border=f"1px solid {BORDER2}",
            border_radius="12px", padding="12px 16px",
        ),
        # Nota técnica
        rx.cond(
            SimplexState.tabla_activa_nota != "",
            rx.box(
                rx.hstack(
                    rx.box(width="3px", height="100%", background=BLUE_L,
                           border_radius="2px", min_height="20px"),
                    rx.text(SimplexState.tabla_activa_nota, size="1", color=TXT2,
                            line_height="1.6"),
                    spacing="3", align_items="flex_start",
                ),
                padding="12px 16px",
                background=f"linear-gradient(135deg, {BLUE_G} 0%, {BG3} 100%)",
                border_radius="12px", margin_top="6px",
                border=f"1px solid {BLUE}30",
            ),
            rx.box(),
        ),
        # Tabla
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            rx.text("Base", size="1", weight="bold",
                                    color=TXT3, letter_spacing="0.1em",
                                    text_transform="uppercase"),
                            background=BG5,
                            border=f"1px solid {BORDER}",
                            padding="10px 18px", text_align="center",
                        ),
                        rx.foreach(
                            SimplexState.tabla_activa_cols,
                            lambda col, j: rx.table.column_header_cell(
                                rx.text(col, size="1", weight="bold",
                                        letter_spacing="0.08em", text_transform="uppercase",
                                        color=rx.cond(SimplexState.tabla_activa_piv_col==j,
                                                      "#60a5fa", TXT3)),
                                background=rx.cond(
                                    SimplexState.tabla_activa_piv_col==j,
                                    f"linear-gradient(180deg, {BLUE_H} 0%, {BLUE_G} 100%)",
                                    BG5),
                                border=f"1px solid {BORDER}",
                                padding="10px 18px", text_align="center",
                                transition="background 0.3s",
                            ),
                        ),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        SimplexState.tabla_activa_filas,
                        lambda fila, i: rx.table.row(
                            rx.table.cell(
                                rx.text(
                                    rx.cond(i==0, "Z", SimplexState.tabla_activa_base[i-1]),
                                    size="2", weight="bold",
                                    color=rx.cond(i==0, GOLD, RED_L),
                                    style=rx.cond(i==0,
                                        {"text_shadow": f"0 0 10px {GOLD}60"},
                                        {"text_shadow": f"0 0 8px {RED}40"}),
                                ),
                                background=rx.cond(i==0,
                                    f"linear-gradient(90deg, {GOLD_G2} 0%, transparent 100%)",
                                    f"linear-gradient(90deg, {RED_G2} 0%, transparent 100%)"),
                                border=f"1px solid {BORDER}",
                                padding="10px 18px", text_align="center",
                            ),
                            rx.foreach(
                                fila,
                                lambda celda, j: rx.table.cell(
                                    rx.text(
                                        celda, size="2",
                                        weight=rx.cond(
                                            (SimplexState.tabla_activa_piv_col==j) &
                                            (SimplexState.tabla_activa_piv_row==i),
                                            "bold", "regular"),
                                        color=rx.cond(
                                            (SimplexState.tabla_activa_piv_col==j) &
                                            (SimplexState.tabla_activa_piv_row==i), "white",
                                            rx.cond(celda.startswith("-") & (i==0),
                                                    NEG, TXT)),
                                        style=rx.cond(
                                            (SimplexState.tabla_activa_piv_col==j) &
                                            (SimplexState.tabla_activa_piv_row==i),
                                            {"text_shadow": "0 0 12px rgba(255,255,255,0.6)"},
                                            {}),
                                    ),
                                    background=rx.cond(
                                        (SimplexState.tabla_activa_piv_col==j) &
                                        (SimplexState.tabla_activa_piv_row==i),
                                        f"linear-gradient(135deg, {BLUE_L} 0%, {BLUE} 100%)",
                                        rx.cond(SimplexState.tabla_activa_piv_col==j,
                                            f"linear-gradient(180deg, {BLUE_G} 0%, transparent 100%)",
                                        rx.cond(SimplexState.tabla_activa_piv_row==i,
                                            f"linear-gradient(90deg, {RED_G} 0%, transparent 100%)",
                                            "transparent"))
                                    ),
                                    border=f"1px solid {BORDER}",
                                    text_align="center", padding="10px 18px",
                                    transition="background 0.2s ease",
                                ),
                            ),
                        ),
                    ),
                ),
                width="100%",
            ),
            border_radius="14px", overflow="hidden",
            border=f"1px solid {BORDER2}",
            box_shadow=f"0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
            margin_top="10px",
        ),
        width="100%", spacing="2", align_items="flex_start",
    )

# ── Navegación pasos ──────────────────────────────────────────────────────────

def step_nav():
    return rx.vstack(
        # Pills circulares
        rx.hstack(
            rx.foreach(
                SimplexState.iter_descripciones,
                lambda desc, i: rx.button(
                    rx.cond(i==0, "I",
                    rx.cond(i==SimplexState.total_iters-1, "✓",
                    rx.cond(desc.contains("Paso A"), "A",
                    rx.cond(desc.contains("Paso B"), "B",
                    rx.cond(desc.contains("Paso C"), "C",
                            i.to_string()))))),
                    on_click=SimplexState.set_iter(i),
                    width="34px", height="34px",
                    border_radius="50%",
                    font_size="11px", font_weight="800",
                    background=rx.cond(SimplexState.iter_activa==i,
                        f"linear-gradient(135deg, {RED} 0%, {RED_D} 100%)",
                        BG5),
                    color=rx.cond(SimplexState.iter_activa==i, "white", TXT2),
                    border=rx.cond(SimplexState.iter_activa==i,
                        f"2px solid {RED_L}",
                        f"1px solid {BORDER2}"),
                    box_shadow=rx.cond(SimplexState.iter_activa==i,
                        f"0 0 16px {RED_G}, 0 0 4px {RED_G}",
                        "none"),
                    cursor="pointer",
                    _hover={"transform": "scale(1.1)",
                            "border_color": RED_L,
                            "box_shadow": f"0 0 10px {RED_G}"},
                    transition="all 0.15s ease",
                    padding="0",
                ),
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # Controles prev/next
        rx.hstack(
            rx.button(
                rx.hstack(
                    rx.icon("chevron-left", size=15),
                    rx.text("Anterior", size="2"),
                    spacing="1",
                ),
                on_click=SimplexState.prev_iter,
                background=BG5, color=TXT2,
                border=f"1px solid {BORDER2}", border_radius="10px",
                padding="0 16px", height="36px",
                _hover={"background": BG4, "color": TXT,
                        "border_color": TXT3,
                        "box_shadow": f"0 0 8px {RED_G}"},
                transition="all 0.15s ease", cursor="pointer",
            ),
            rx.box(
                rx.hstack(
                    rx.text(SimplexState.iter_activa.to_string(),
                            size="2", weight="bold", color=RED_L),
                    rx.text("/", size="2", color=TXT3),
                    rx.text((SimplexState.total_iters-1).to_string(),
                            size="2", weight="bold", color=TXT2),
                    spacing="1", align_items="center",
                ),
                background=BG5,
                border=f"1px solid {BORDER2}",
                border_radius="10px", padding="0 16px", height="36px",
                display="flex", align_items="center",
            ),
            rx.button(
                rx.hstack(
                    rx.text("Siguiente", size="2"),
                    rx.icon("chevron-right", size=15),
                    spacing="1",
                ),
                on_click=SimplexState.next_iter,
                background=BG5, color=TXT2,
                border=f"1px solid {BORDER2}", border_radius="10px",
                padding="0 16px", height="36px",
                _hover={"background": BG4, "color": TXT,
                        "border_color": TXT3,
                        "box_shadow": f"0 0 8px {RED_G}"},
                transition="all 0.15s ease", cursor="pointer",
            ),
            spacing="2",
        ),
        spacing="3", width="100%",
    )

# ── Formulario ────────────────────────────────────────────────────────────────

def form_panel():
    return glow_card(
        # Decorador superior
        rx.box(
            height="3px",
            background=f"linear-gradient(90deg, {RED} 0%, {GOLD} 50%, {RED} 100%)",
            position="absolute", top="0", left="0", right="0",
            border_radius="20px 20px 0 0",
        ),

        # Título sección
        rx.hstack(
            rx.box(
                rx.icon("pencil-ruler", size=16, color=RED_L),
                background=RED_G,
                border_radius="10px", padding="8px",
                border=f"1px solid {RED}30",
            ),
            rx.vstack(
                rx.text("Ingresa el Problema", size="4", weight="bold", color=TXT),
                rx.text("Programación Lineal — Simplex", size="1", color=TXT3),
                spacing="0",
            ),
            spacing="3", align_items="center", margin_bottom="22px",
        ),

        # Dimensiones
        section_label("Dimensiones del problema"),
        rx.hstack(
            rx.vstack(
                rx.text("Variables de decisión", size="1", color=TXT3),
                styled_select(["2","3","4"], SimplexState.n_vars.to_string(), SimplexState.set_n_vars),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Restricciones", size="1", color=TXT3),
                styled_select(["2","3","4"], SimplexState.n_cons.to_string(), SimplexState.set_n_cons),
                spacing="1",
            ),
            rx.vstack(
                rx.text("No negatividades", size="1", color=TXT3),
                rx.box(
                    rx.text("x₁, x₂... ≥ 0", size="1", weight="bold", color=GREEN_L),
                    background=GREEN_G,
                    border=f"1px solid {GREEN_L}30",
                    border_radius="10px", padding="6px 12px",
                    height="34px", display="flex", align_items="center",
                ),
                spacing="1",
            ),
            spacing="5", flex_wrap="wrap",
        ),

        accent_line(RED),

        # Función objetivo
        section_label("Función objetivo"),
        rx.hstack(
            rx.box(
                rx.hstack(
                    rx.icon("trending-up", size=14, color=GOLD),
                    rx.text("Maximizar", size="1", weight="bold", color=GOLD,
                            letter_spacing="0.08em"),
                    spacing="2", align_items="center",
                ),
                background=GOLD_G, border=f"1px solid {GOLD}30",
                border_radius="8px", padding="5px 14px",
                box_shadow=f"0 0 12px {GOLD_G}",
            ),
        ),
        rx.hstack(
            rx.text("Z =", size="4", weight="bold", color=GOLD,
                    style={"text_shadow": f"0 0 16px {GOLD}60"}),
            styled_input(SimplexState.obj[0], lambda v: SimplexState.set_obj(0,v)),
            lbl("x₁"),
            rx.cond(SimplexState.n_vars>=2,
                rx.hstack(lbl("+"), styled_input(SimplexState.obj[1], lambda v: SimplexState.set_obj(1,v)), lbl("x₂"), spacing="2"), rx.box()),
            rx.cond(SimplexState.n_vars>=3,
                rx.hstack(lbl("+"), styled_input(SimplexState.obj[2], lambda v: SimplexState.set_obj(2,v)), lbl("x₃"), spacing="2"), rx.box()),
            rx.cond(SimplexState.n_vars>=4,
                rx.hstack(lbl("+"), styled_input(SimplexState.obj[3], lambda v: SimplexState.set_obj(3,v)), lbl("x₄"), spacing="2"), rx.box()),
            spacing="2", flex_wrap="wrap", align_items="center", margin_top="10px",
        ),

        accent_line(GOLD),

        # Restricciones
        section_label("Restricciones"),
        cons_row(0), cons_row(1),
        rx.cond(SimplexState.n_cons>=3, cons_row(2), rx.box()),
        rx.cond(SimplexState.n_cons>=4, cons_row(3), rx.box()),

        accent_line(RED),

        # Botones de acción
        rx.hstack(
            rx.button(
                rx.cond(
                    SimplexState.loading,
                    rx.hstack(rx.spinner(size="2"), rx.text("Calculando...", size="2"), spacing="2"),
                    rx.hstack(rx.icon("play", size=15), rx.text("Resolver", size="2", weight="bold"), spacing="2"),
                ),
                on_click=SimplexState.resolver,
                loading=SimplexState.loading,
                background=f"linear-gradient(135deg, {RED} 0%, {RED_D} 100%)",
                color="white", border_radius="12px", border="none",
                padding="0 26px", height="44px",
                box_shadow=f"0 4px 20px {RED_G}, 0 0 0 1px {RED}40",
                _hover={"transform": "translateY(-2px)",
                        "box_shadow": f"0 8px 32px {RED_G}, 0 0 20px {RED_G}"},
                _active={"transform": "translateY(0)"},
                transition="all 0.2s ease", cursor="pointer",
            ),
            rx.button(
                rx.hstack(rx.icon("book-open", size=14), rx.text("Ejemplo del profe", size="2"), spacing="2"),
                on_click=SimplexState.cargar_ejemplo,
                background=BG5, color=TXT2,
                border=f"1px solid {BORDER2}", border_radius="12px",
                padding="0 18px", height="44px",
                _hover={"background": BG4, "color": TXT,
                        "border_color": GOLD,
                        "box_shadow": f"0 0 12px {GOLD_G}"},
                transition="all 0.15s ease", cursor="pointer",
            ),
            rx.button(
                rx.icon("rotate-ccw", size=15),
                on_click=SimplexState.limpiar,
                background="transparent", color=TXT3,
                border=f"1px solid {BORDER}", border_radius="12px",
                padding="0 14px", height="44px",
                _hover={"background": BG5, "color": NEG,
                        "border_color": NEG,
                        "box_shadow": f"0 0 10px rgba(241,148,138,0.2)"},
                transition="all 0.15s ease", cursor="pointer",
            ),
            spacing="2", flex_wrap="wrap",
        ),

        # Error
        rx.cond(
            SimplexState.error_msg != "",
            rx.box(
                rx.hstack(
                    rx.icon("circle-x", size=16, color=NEG),
                    rx.text(SimplexState.error_msg, size="2", color=NEG),
                    spacing="2", align_items="center",
                ),
                background="rgba(241,148,138,0.07)",
                border=f"1px solid rgba(241,148,138,0.2)",
                border_radius="12px", padding="12px 16px", margin_top="16px",
            ),
            rx.box(),
        ),

        width="100%", max_width="580px",
    )

# ── Panel resultados ──────────────────────────────────────────────────────────

def result_panel():
    return rx.cond(
        SimplexState.resuelto,
        rx.vstack(

            # ── Card solución óptima ──────────────────────────────────────
            glow_card(
                rx.box(
                    height="3px",
                    background=f"linear-gradient(90deg, {GOLD} 0%, {GREEN_L} 50%, {GOLD} 100%)",
                    position="absolute", top="0", left="0", right="0",
                    border_radius="20px 20px 0 0",
                ),
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("trophy", size=17, color=GOLD),
                            background=GOLD_G,
                            border_radius="10px", padding="8px",
                            border=f"1px solid {GOLD}30",
                            box_shadow=f"0 0 16px {GOLD_G}",
                        ),
                        rx.vstack(
                            rx.text("Solución Óptima", size="4", weight="bold", color=TXT),
                            rx.text("Valor máximo encontrado", size="1", color=TXT3),
                            spacing="0",
                        ),
                        spacing="3", align_items="center",
                    ),
                    rx.spacer(),
                    rx.box(
                        rx.hstack(
                            rx.icon("check-circle-2", size=13, color=GREEN_L),
                            rx.text("ÓPTIMO", size="1", weight="bold",
                                    color=GREEN_L, letter_spacing="0.1em"),
                            spacing="1", align_items="center",
                        ),
                        background=GREEN_G,
                        border=f"1px solid {GREEN_L}30",
                        border_radius="999px", padding="4px 14px",
                        box_shadow=f"0 0 12px {GREEN_G}",
                    ),
                    align_items="center", margin_bottom="22px",
                ),

                # Métricas
                rx.hstack(
                    rx.box(
                        rx.text("Z máximo", size="1", color=TXT3,
                                letter_spacing="0.1em", text_transform="uppercase"),
                        rx.text(SimplexState.z_optimo.to_string(), size="8",
                                weight="bold", color=GOLD,
                                style={"text_shadow": f"0 0 24px {GOLD}80",
                                       "line_height":"1",
                                       "font_variant_numeric":"tabular-nums"}),
                        background=f"linear-gradient(135deg, {GOLD_G} 0%, {GOLD_G2} 100%)",
                        border=f"1px solid {GOLD}25",
                        border_radius="16px", padding="20px 28px",
                        min_width="140px",
                        box_shadow=f"0 4px 24px {GOLD_G}, inset 0 1px 0 {GOLD}20",
                    ),
                    rx.foreach(
                        SimplexState.variables_decision,
                        lambda v, i: rx.box(
                            rx.text(f"x{i+1}", size="1", color=TXT3,
                                    letter_spacing="0.1em", text_transform="uppercase"),
                            rx.text(v.to_string(), size="6", weight="bold", color=RED_L,
                                    style={"text_shadow": f"0 0 16px {RED}60",
                                           "line_height":"1",
                                           "font_variant_numeric":"tabular-nums"}),
                            background=RED_G2,
                            border=f"1px solid {RED}25",
                            border_radius="16px", padding="20px 28px",
                            min_width="110px",
                            box_shadow=f"0 4px 16px {RED_G2}",
                        ),
                    ),
                    spacing="3", flex_wrap="wrap",
                ),

                accent_line(GOLD),

                # Holguras
                rx.text("Variables de Holgura", size="1", color=TXT3,
                        letter_spacing="0.1em", text_transform="uppercase",
                        margin_bottom="12px"),
                rx.hstack(
                    rx.foreach(
                        SimplexState.holguras,
                        lambda v, i: rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.text(f"S{i+1}", size="2", weight="bold",
                                            color=rx.cond(v==0, ORANGE, BLUE_L)),
                                    background=rx.cond(v==0, ORANGE_G, BLUE_G),
                                    border=rx.cond(v==0,
                                        f"1px solid {ORANGE}30",
                                        f"1px solid {BLUE_L}30"),
                                    border_radius="8px", padding="3px 10px",
                                ),
                                rx.text("=", size="2", color=TXT3),
                                rx.text(v.to_string(), size="3", weight="bold", color=TXT),
                                spacing="2", align_items="center",
                            ),
                            rx.hstack(
                                rx.box(
                                    width="6px", height="6px",
                                    border_radius="50%",
                                    background=rx.cond(v==0, ORANGE, GREEN_L),
                                    box_shadow=rx.cond(v==0,
                                        f"0 0 6px {ORANGE}",
                                        f"0 0 6px {GREEN_L}"),
                                ),
                                rx.text(
                                    rx.cond(v==0, "Restricción activa", "Capacidad sobrante"),
                                    size="1",
                                    color=rx.cond(v==0, ORANGE, GREEN_L),
                                ),
                                spacing="2", align_items="center",
                            ),
                            background=BG4,
                            border_radius="14px", padding="14px 18px",
                            border=rx.cond(v==0,
                                f"1px solid {ORANGE}20",
                                f"1px solid {BLUE_L}20"),
                            margin_top="6px",
                        ),
                    ),
                    spacing="3", flex_wrap="wrap",
                ),

                # Mensaje
                rx.box(
                    rx.hstack(
                        rx.icon("check-circle-2", size=15, color=GREEN_L),
                        rx.text(SimplexState.mensaje, size="2", color=GREEN_L),
                        spacing="2", align_items="center",
                    ),
                    background=GREEN_G,
                    border=f"1px solid {GREEN_L}25",
                    border_radius="12px", padding="12px 18px", margin_top="16px",
                    box_shadow=f"0 0 16px {GREEN_G}",
                ),
                width="100%",
            ),

            # ── Card iteraciones ──────────────────────────────────────────
            glow_card(
                rx.box(
                    height="3px",
                    background=f"linear-gradient(90deg, {BLUE} 0%, {BLUE_L} 50%, {BLUE} 100%)",
                    position="absolute", top="0", left="0", right="0",
                    border_radius="20px 20px 0 0",
                ),
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("table-2", size=16, color=BLUE_L),
                            background=BLUE_G,
                            border_radius="10px", padding="8px",
                            border=f"1px solid {BLUE_L}30",
                            box_shadow=f"0 0 12px {BLUE_G}",
                        ),
                        rx.vstack(
                            rx.text("Iteraciones Paso a Paso", size="4",
                                    weight="bold", color=TXT),
                            rx.text("Seguimiento completo del algoritmo",
                                    size="1", color=TXT3),
                            spacing="0",
                        ),
                        spacing="3", align_items="center",
                    ),
                    rx.spacer(),
                    rx.box(
                        rx.hstack(
                            rx.icon("layers", size=12, color=BLUE_L),
                            rx.text(SimplexState.total_iters.to_string() + " pasos",
                                    size="1", weight="bold", color=BLUE_L),
                            spacing="1", align_items="center",
                        ),
                        background=BLUE_G,
                        border=f"1px solid {BLUE_L}25",
                        border_radius="999px", padding="4px 14px",
                    ),
                    align_items="center", margin_bottom="20px",
                ),

                step_nav(),
                accent_line(BLUE_L),
                tabla_simplex(),

                width="100%", overflow_x="auto",
            ),

            spacing="5", width="100%", align_items="stretch",
        ),

        # ── Empty state ───────────────────────────────────────────────────
        glow_card(
            rx.vstack(
                rx.box(
                    rx.icon("sigma", size=36, color=TXT3),
                    background=BG4,
                    border_radius="50%", padding="22px",
                    border=f"1px solid {BORDER2}",
                    box_shadow=f"0 0 30px {RED_G2}",
                    margin_bottom="6px",
                ),
                rx.text("Listo para resolver", size="5", weight="bold", color=TXT2),
                rx.text("Configura el problema y presiona Resolver",
                        size="2", color=TXT3),
                rx.hstack(
                    chip("x₁, x₂ ≥ 0", GREEN_L, GREEN_G),
                    chip("Tipo ≤", BLUE_L, BLUE_G),
                    chip("Maximización", GOLD, GOLD_G),
                    spacing="2", flex_wrap="wrap", justify_content="center",
                ),
                spacing="3", align_items="center", padding="48px 20px",
            ),
            width="100%", text_align="center",
        ),
    )

# ── Página ────────────────────────────────────────────────────────────────────

def index():
    return rx.box(

        # ── Navbar ───────────────────────────────────────────────────────
        rx.box(
            rx.hstack(
                # Logo UP + título
                rx.hstack(
                    rx.image(
                        src="/UP-logo.png",
                        width="110px", height="110px",
                        object_fit="contain",
                        style={"filter": "drop-shadow(0 0 8px rgba(192,57,43,0.4))"},
                    ),
                    rx.box(
                        width="1px", height="36px",
                        background=f"linear-gradient(180deg, transparent, {BORDER2}, transparent)",
                    ),
                    rx.vstack(
                        rx.text("Método Simplex", size="4", weight="bold", color=TXT,
                                style={"letter_spacing": "-0.01em"}),
                        rx.hstack(
                            rx.text("Universidad de Panamá", size="1", color=TXT3),
                            rx.text("•", size="1", color=TXT3),
                            rx.text("Investigación de Operaciones", size="1", color=TXT3),
                            spacing="1",
                        ),
                        spacing="0",
                    ),
                    spacing="3", align_items="center",
                ),
                rx.spacer(),
                # Badges derechos
                rx.hstack(
                    rx.box(
                        rx.hstack(
                            rx.icon("maximize-2", size=12, color=GOLD),
                            rx.text("Maximización", size="1", weight="bold", color=GOLD),
                            spacing="1", align_items="center",
                        ),
                        background=GOLD_G, border=f"1px solid {GOLD}25",
                        border_radius="999px", padding="5px 14px",
                        box_shadow=f"0 0 10px {GOLD_G}",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.icon("shield-check", size=12, color=GREEN_L),
                            rx.text("x ≥ 0  implícito", size="1", weight="bold", color=GREEN_L),
                            spacing="1", align_items="center",
                        ),
                        background=GREEN_G, border=f"1px solid {GREEN_L}25",
                        border_radius="999px", padding="5px 14px",
                        display=["none","none","flex"],
                    ),
                    spacing="2",
                ),
                align_items="center", width="100%",
            ),
            background="rgba(10,13,19,0.92)",
            border_bottom=f"1px solid {BORDER}",
            padding="12px 32px",
            box_shadow=f"0 4px 30px rgba(0,0,0,0.7), 0 1px 0 {BORDER2}",
            style={"backdrop_filter": "blur(20px)"},
            position="sticky", top="0", z_index="100",
        ),

        # ── Contenido principal ───────────────────────────────────────────
        rx.box(
            rx.flex(
                form_panel(),
                result_panel(),
                direction="row", gap="28px",
                flex_wrap="wrap", align_items="flex_start",
            ),
            padding="32px",
            max_width="1500px", margin="0 auto",
        ),

        background=BG,
        min_height="100vh",
        style={
            "background": (
                f"radial-gradient(ellipse at 10% 0%, rgba(192,57,43,0.10) 0%, transparent 45%), "
                f"radial-gradient(ellipse at 90% 100%, rgba(36,113,163,0.08) 0%, transparent 45%), "
                f"radial-gradient(ellipse at 50% 50%, rgba(241,196,15,0.03) 0%, transparent 60%), "
                f"{BG}"
            )
        },
    )


app = rx.App(
    style={
        "background": BG,
        "font_family": "'Inter', 'Segoe UI', system-ui, sans-serif",
    }
)
app.add_page(index, route="/", title="Simplex — Universidad de Panamá")
