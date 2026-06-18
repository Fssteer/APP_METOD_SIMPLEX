import flet as ft
import httpx
import asyncio
from typing import List

BACKEND_URL = "http://192.168.137.37:8080"

# ── Paleta (igual al web) ─────────────────────────────────────────────────────
BG      = "#070a10"
BG2     = "#0d1119"
BG3     = "#131824"
BG4     = "#191f2e"
BG5     = "#1e2538"
BORDER  = "#1e2840"
BORDER2 = "#2d3a55"
RED     = "#C0392B"
RED_L   = "#E74C3C"
GOLD    = "#F1C40F"
GOLD_D  = "#D4AC0D"
BLUE    = "#2471A3"
BLUE_L  = "#3498DB"
GREEN   = "#27AE60"
ORANGE  = "#E67E22"
TXT     = "#dde3f0"
TXT2    = "#7a89a8"
TXT3    = "#3d4d6a"
NEG     = "#F1948A"
ROW_COLORS = [RED_L, BLUE_L, GREEN, GOLD_D]

def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9: return str(int(round(v)))
    for d in range(1, 33):
        n = round(v * d)
        if abs(n / d - v) < 1e-9: return f"{n}/{d}"
    return f"{v:.4f}"

# ── Helpers ───────────────────────────────────────────────────────────────────
def section_title(text):
    return ft.Row([
        ft.Container(width=3, height=14,
            gradient=ft.LinearGradient([RED, GOLD],
                begin=ft.Alignment(0,-1), end=ft.Alignment(0,1)),
            border_radius=2),
        ft.Text(text.upper(), size=11, weight=ft.FontWeight.BOLD,
                color=TXT2, letter_spacing=1.5),
    ], spacing=8)

def divider(color=RED):
    return ft.Container(height=1,
        gradient=ft.LinearGradient([color,"transparent"],
            begin=ft.Alignment(-1,0), end=ft.Alignment(1,0)),
        margin=ft.margin.symmetric(vertical=12), opacity=0.5)

def badge(text, color, bg):
    return ft.Container(
        content=ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=color),
        bgcolor=bg, border_radius=999,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border=ft.border.all(1, f"{color}40"))

def field(value="", width=68):
    return ft.TextField(
        value=value, width=width,
        text_align=ft.TextAlign.CENTER,
        text_size=13, color=TXT, bgcolor=BG4,
        border_color=BORDER2, focused_border_color=RED_L,
        border_radius=10,
        content_padding=ft.padding.symmetric(horizontal=6, vertical=8),
        keyboard_type=ft.KeyboardType.NUMBER)

def card_container(content):
    return ft.Container(
        content=content, bgcolor=BG2,
        border_radius=16, padding=16,
        border=ft.border.all(1, BORDER2),
        shadow=ft.BoxShadow(blur_radius=20, color="#00000055",
                            offset=ft.Offset(0,4)))

def primary_btn(text, icon, on_click):
    return ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(icon, size=15, color="white"),
            ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color="white"),
        ], spacing=6, tight=True),
        style=ft.ButtonStyle(
            bgcolor=RED, overlay_color=f"{RED}CC",
            shape=ft.RoundedRectangleBorder(radius=12),
            shadow_color=f"{RED}60", elevation=6,
            padding=ft.padding.symmetric(horizontal=18, vertical=11)),
        on_click=on_click)

def secondary_btn(text, icon, on_click):
    return ft.OutlinedButton(
        content=ft.Row([
            ft.Icon(icon, size=14, color=TXT2),
            ft.Text(text, size=12, color=TXT2),
        ], spacing=6, tight=True),
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, BORDER2),
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color=BG4,
            padding=ft.padding.symmetric(horizontal=14, vertical=11)),
        on_click=on_click)

# ── App ───────────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title = "Simplex — UP"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    state = {"n_vars": 2, "n_cons": 2, "iteraciones": [], "iter_actual": 0}
    obj_f: List[ft.TextField] = []
    con_f: List[List[ft.TextField]] = []
    rhs_f: List[ft.TextField] = []

    # Referencias dinámicas
    form_col     = ft.Column(spacing=8)
    sol_card     = ft.Ref[ft.Container]()
    iter_card    = ft.Ref[ft.Container]()
    z_txt        = ft.Text("", size=28, weight=ft.FontWeight.BOLD, color=GOLD,
                            text_align=ft.TextAlign.CENTER)
    vars_row     = ft.Row(spacing=8, wrap=True)
    hol_row      = ft.Row(spacing=8, wrap=True)
    msg_txt      = ft.Text("", size=12, color=GREEN)
    err_box      = ft.Container(visible=False, bgcolor=f"{NEG}12",
                                border_radius=10, padding=10,
                                border=ft.border.all(1, f"{NEG}30"))
    err_txt      = ft.Text("", size=12, color=NEG)
    loading      = ft.ProgressRing(visible=False, color=RED,
                                   stroke_width=2, width=22, height=22)
    tabs_row     = ft.Row(spacing=6, wrap=True)
    counter_txt  = ft.Text("0 / 0", size=12, weight=ft.FontWeight.BOLD, color=TXT2)
    desc_txt     = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=TXT)
    nota_box     = ft.Container(visible=False, bgcolor=f"{BLUE}18",
                                border_radius=8, padding=10,
                                border=ft.border.all(1, f"{BLUE_L}30"))
    nota_txt     = ft.Text("", size=11, color=TXT2)
    tabla_col    = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0)

    nota_box.content = ft.Row([
        ft.Container(width=3, bgcolor=BLUE_L, border_radius=2), nota_txt
    ], spacing=8)
    err_box.content = ft.Row([
        ft.Icon(ft.Icons.ERROR_OUTLINE, color=NEG, size=15), err_txt
    ], spacing=6)

    def show_error(msg):
        err_box.visible = bool(msg); err_txt.value = msg; page.update()

    def build_form():
        nonlocal obj_f, con_f, rhs_f
        nv = state["n_vars"]; nc = state["n_cons"]
        obj_f = [field() for _ in range(4)]
        con_f = [[field() for _ in range(4)] for _ in range(4)]
        rhs_f = [field() for _ in range(4)]

        rows = [section_title("Función objetivo")]
        obj_row = [ft.Text("Z =", size=15, weight=ft.FontWeight.BOLD, color=GOLD)]
        for j in range(nv):
            if j > 0: obj_row.append(ft.Text("+", size=13, color=TXT2))
            obj_row += [obj_f[j], ft.Text(f"x{j+1}", size=12, color=TXT2)]
        rows.append(ft.Row(obj_row, spacing=5, wrap=True))
        rows.append(divider(GOLD))
        rows.append(section_title("Restricciones"))
        for i in range(nc):
            c = ROW_COLORS[i % 4]
            r = [ft.Container(
                content=ft.Text(f"R{i+1}", size=11, weight=ft.FontWeight.BOLD, color=c),
                bgcolor=f"{c}20", border_radius=7,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border=ft.border.all(1, f"{c}40"))]
            for j in range(nv):
                if j > 0: r.append(ft.Text("+", size=13, color=TXT2))
                r += [con_f[i][j], ft.Text(f"x{j+1}", size=12, color=TXT2)]
            r += [ft.Text("≤", size=15, weight=ft.FontWeight.BOLD, color=GOLD),
                  rhs_f[i]]
            rows.append(ft.Row(r, spacing=5, wrap=True))
        form_col.controls = rows
        page.update()

    def load_example(_=None):
        state["n_vars"] = 2; state["n_cons"] = 2
        build_form()
        obj_f[0].value="50"; obj_f[1].value="80"
        con_f[0][0].value="1"; con_f[0][1].value="2"; rhs_f[0].value="120"
        con_f[1][0].value="1"; con_f[1][1].value="1"; rhs_f[1].value="90"
        clear_result(); page.update()

    def clear_result(_=None):
        state["iteraciones"]=[]; state["iter_actual"]=0
        if sol_card.current:  sol_card.current.visible = False
        if iter_card.current: iter_card.current.visible = False
        show_error("")

    def render_tabla(idx: int):
        state["iter_actual"] = idx
        iters = state["iteraciones"]
        it = iters[idx]
        total = len(iters)

        desc_txt.value = it["descripcion"]
        nota = it.get("nota_pivote") or ""
        nota_txt.value = nota; nota_box.visible = bool(nota)
        counter_txt.value = f"{idx} / {total-1}"

        pc = it["columna_pivote"] if it["columna_pivote"] is not None else -1
        pr = it["fila_pivote"]    if it["fila_pivote"]    is not None else -1
        cols = it["nombres_columnas"]
        base = it["base"]
        tabla = it["tabla"]

        # Tabla
        header = [ft.DataColumn(ft.Text("Base", size=10, weight=ft.FontWeight.BOLD,
                                         color=TXT3, italic=True))]
        for j, col in enumerate(cols):
            header.append(ft.DataColumn(ft.Container(
                content=ft.Text(col, size=10, weight=ft.FontWeight.BOLD,
                                color=BLUE_L if j==pc else TXT3),
                bgcolor=f"{BLUE_L}30" if j==pc else "transparent",
                border_radius=5, padding=ft.padding.symmetric(horizontal=4, vertical=2))))

        rows = []
        for i, fila in enumerate(tabla):
            bname = "Z" if i==0 else base[i-1]
            cells = [ft.DataCell(ft.Text(bname, size=12, weight=ft.FontWeight.BOLD,
                                          color=GOLD if i==0 else RED_L))]
            for j, val in enumerate(fila):
                is_piv = (j==pc and i==pr)
                fval = _fmt(val)
                is_neg = fval.startswith("-") and i==0
                tc = "white" if is_piv else (NEG if is_neg else TXT)
                cbg = (BLUE_L if is_piv else
                       (f"{BLUE}40" if j==pc else
                        (f"{RED}30" if i==pr else "transparent")))
                cells.append(ft.DataCell(ft.Container(
                    content=ft.Text(fval, size=12, color=tc,
                                    weight=ft.FontWeight.BOLD if is_piv else ft.FontWeight.NORMAL),
                    bgcolor=cbg, border_radius=5,
                    padding=ft.padding.symmetric(horizontal=6, vertical=3))))
            rbg = f"{GOLD}08" if i==0 else f"{RED}08"
            rows.append(ft.DataRow(cells=cells,
                                   color=ft.MaterialStatePropertyAll(rbg)))

        tabla_col.controls = [ft.DataTable(
            columns=header, rows=rows,
            bgcolor=BG3, border=ft.border.all(1, BORDER),
            border_radius=12,
            heading_row_color=ft.MaterialStatePropertyAll(BG4),
            data_row_min_height=38, column_spacing=12,
            horizontal_lines=ft.border.BorderSide(1, BORDER),
            vertical_lines=ft.border.BorderSide(1, BORDER),
        )]

        # Pills
        pills = []
        for k in range(total):
            dk = iters[k]["descripcion"]
            lbl = ("I" if k==0 else "✓" if k==total-1 else
                   "A" if "Paso A" in dk else
                   "B" if "Paso B" in dk else
                   "C" if "Paso C" in dk else str(k))
            is_a = k==idx; kk=k
            pills.append(ft.Container(
                content=ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD,
                                color="white" if is_a else TXT2,
                                text_align=ft.TextAlign.CENTER),
                width=32, height=32, border_radius=16,
                bgcolor=RED if is_a else BG5,
                border=ft.border.all(2 if is_a else 1,
                                     RED_L if is_a else BORDER2),
                shadow=ft.BoxShadow(blur_radius=10,
                                    color=f"{RED}50" if is_a else "transparent"),
                alignment=ft.alignment.center,
                on_click=lambda e, ki=kk: render_tabla(ki), ink=True))
        tabs_row.controls = pills
        page.update()

    async def resolver_async(_=None):
        show_error(""); loading.visible=True; page.update()
        try:
            nv=state["n_vars"]; nc=state["n_cons"]
            obj_vals=[]
            for j in range(nv):
                v=obj_f[j].value.strip()
                if not v: show_error(f"Falta coef. en Z x{j+1}"); return
                obj_vals.append(float(v))
            A=[]
            for i in range(nc):
                row=[]
                for j in range(nv):
                    v=con_f[i][j].value.strip()
                    if not v: show_error(f"Falta coef. R{i+1} x{j+1}"); return
                    row.append(float(v))
                A.append(row)
            b_vals=[]
            for i in range(nc):
                v=rhs_f[i].value.strip()
                if not v: show_error(f"Falta RHS R{i+1}"); return
                b_vals.append(float(v))

            async with httpx.AsyncClient(timeout=15) as client:
                resp=await client.post(f"{BACKEND_URL}/simplex",
                    json={"objetivo":obj_vals,"restricciones":A,"rhs":b_vals})
                data=resp.json()

            if not data.get("exito"):
                show_error(data.get("mensaje","Error")); return

            state["iteraciones"]=data["iteraciones"]
            z_txt.value=str(data["z_optimo"])

            # Variables
            vchips=[]
            for j,val in enumerate(data["variables_decision"]):
                vchips.append(ft.Container(
                    content=ft.Column([
                        ft.Text(f"x{j+1}", size=10, color=TXT3,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(str(val), size=20, weight=ft.FontWeight.BOLD,
                                color=RED_L, text_align=ft.TextAlign.CENTER),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=f"{RED}18", border_radius=12,
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border=ft.border.all(1, f"{RED}30"), min_width=80))
            vars_row.controls=vchips

            # Holguras
            hchips=[]
            for j,val in enumerate(data["holguras"]):
                is_act=abs(val)<1e-9; c=ORANGE if is_act else BLUE_L
                hchips.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"S{j+1}", size=11,
                                                weight=ft.FontWeight.BOLD, color=c),
                                bgcolor=f"{c}20", border_radius=5,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2)),
                            ft.Text("=", size=12, color=TXT3),
                            ft.Text(str(val), size=14,
                                    weight=ft.FontWeight.BOLD, color=TXT),
                        ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row([
                            ft.Container(width=5,height=5,border_radius=3,bgcolor=c),
                            ft.Text("Activa" if is_act else "Sobrante",
                                    size=10, color=c),
                        ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=BG4, border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border=ft.border.all(1, f"{c}30")))
            hol_row.controls=hchips
            msg_txt.value=data.get("mensaje","")

            sol_card.current.visible=True
            iter_card.current.visible=True
            render_tabla(0)

        except httpx.ConnectError:
            show_error("No se pudo conectar al backend.\nVerifica que esté corriendo en la misma red WiFi.")
        except Exception as e:
            show_error(f"Error: {e}")
        finally:
            loading.visible=False; page.update()

    def resolver(e): asyncio.create_task(resolver_async(e))

    def change_vars(e): state["n_vars"]=int(e.control.value); build_form()
    def change_cons(e): state["n_cons"]=int(e.control.value); build_form()

    # ── Layout ────────────────────────────────────────────────────────────────
    page.add(
        # Navbar
        ft.Container(
            content=ft.Row([
                ft.Image(src="/UP-logo.png", width=40, height=40,
                         fit=ft.ImageFit.CONTAIN),
                ft.Container(width=1, height=32, bgcolor=BORDER2),
                ft.Column([
                    ft.Text("Método Simplex", size=15,
                            weight=ft.FontWeight.BOLD, color=TXT),
                    ft.Text("Universidad de Panamá · IO", size=10, color=TXT3),
                ], spacing=0, expand=True),
                badge("Maximización", GOLD, f"{GOLD}18"),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=BG2, padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border=ft.border.only(bottom=ft.border.BorderSide(1, BORDER2)),
            shadow=ft.BoxShadow(blur_radius=16, color="#00000070")),

        # Contenido
        ft.Container(
            padding=14,
            content=ft.Column([

                # ── Card formulario ───────────────────────────────────────
                card_container(ft.Column([
                    # Encabezado
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.FUNCTIONS, color=RED_L, size=16),
                            bgcolor=f"{RED}18", border_radius=8, padding=7,
                            border=ft.border.all(1, f"{RED}30")),
                        ft.Column([
                            ft.Text("Ingresa el Problema", size=14,
                                    weight=ft.FontWeight.BOLD, color=TXT),
                            ft.Text("Programación Lineal", size=10, color=TXT3),
                        ], spacing=0),
                    ], spacing=10),

                    divider(RED),

                    # Dimensiones
                    ft.Row([
                        ft.Column([
                            ft.Text("Variables", size=10, color=TXT3),
                            ft.Dropdown(value="2", width=85, bgcolor=BG4, color=TXT,
                                border_color=BORDER2, focused_border_color=RED_L,
                                border_radius=10, on_change=change_vars,
                                options=[ft.dropdown.Option(str(i)) for i in [2,3,4]]),
                        ], spacing=4),
                        ft.Column([
                            ft.Text("Restricciones", size=10, color=TXT3),
                            ft.Dropdown(value="2", width=110, bgcolor=BG4, color=TXT,
                                border_color=BORDER2, focused_border_color=RED_L,
                                border_radius=10, on_change=change_cons,
                                options=[ft.dropdown.Option(str(i)) for i in [2,3,4]]),
                        ], spacing=4),
                        ft.Column([
                            ft.Text("No negatividades", size=10, color=TXT3),
                            ft.Container(
                                content=ft.Text("x ≥ 0  implícito", size=11,
                                                weight=ft.FontWeight.BOLD, color=GREEN),
                                bgcolor=f"{GREEN}18", border_radius=8, padding=7,
                                border=ft.border.all(1, f"{GREEN}30")),
                        ], spacing=4),
                    ], spacing=12, wrap=True),

                    divider(RED),
                    form_col,
                    divider(RED),

                    # Botones
                    ft.Row([
                        primary_btn("Resolver", ft.Icons.PLAY_ARROW_ROUNDED, resolver),
                        secondary_btn("Ejemplo", ft.Icons.BOOK_OUTLINED, load_example),
                        ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color=TXT3,
                            on_click=clear_result,
                            style=ft.ButtonStyle(
                                bgcolor=BG5,
                                shape=ft.RoundedRectangleBorder(radius=12),
                                side=ft.BorderSide(1, BORDER))),
                    ], spacing=8, wrap=True),

                    loading, err_box,
                ], spacing=10)),

                ft.Container(height=14),

                # ── Card solución ─────────────────────────────────────────
                ft.Container(ref=sol_card, visible=False,
                    content=ft.Column([
                        ft.Container(height=3,
                            gradient=ft.LinearGradient([GOLD, GREEN, GOLD],
                                begin=ft.Alignment(-1,0), end=ft.Alignment(1,0)),
                            border_radius=ft.border_radius.only(
                                top_left=16, top_right=16)),
                        ft.Container(padding=16,
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.EMOJI_EVENTS,
                                                        color=GOLD, size=16),
                                        bgcolor=f"{GOLD}18", border_radius=8,
                                        padding=7, border=ft.border.all(1,f"{GOLD}30")),
                                    ft.Column([
                                        ft.Text("Solución Óptima", size=14,
                                                weight=ft.FontWeight.BOLD, color=TXT),
                                        ft.Text("Valor máximo encontrado",
                                                size=10, color=TXT3),
                                    ], spacing=0),
                                    ft.Container(expand=True),
                                    badge("ÓPTIMO", GREEN, f"{GREEN}18"),
                                ], spacing=10,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),

                                ft.Container(height=6),

                                ft.Row([
                                    ft.Container(
                                        content=ft.Column([
                                            ft.Text("Z máximo", size=10, color=TXT3,
                                                    text_align=ft.TextAlign.CENTER),
                                            z_txt,
                                        ], spacing=2,
                                           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                        bgcolor=f"{GOLD}10", border_radius=12,
                                        padding=14,
                                        border=ft.border.all(1,f"{GOLD}25"),
                                        min_width=120),
                                    vars_row,
                                ], spacing=10, wrap=True,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),

                                ft.Divider(color=BORDER, height=20),

                                ft.Text("Variables de Holgura", size=10,
                                        color=TXT3, letter_spacing=1.2),
                                hol_row,
                                ft.Container(height=4),
                                ft.Container(
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE,
                                                color=GREEN, size=14),
                                        msg_txt,
                                    ], spacing=6),
                                    bgcolor=f"{GREEN}12", border_radius=10,
                                    padding=10,
                                    border=ft.border.all(1,f"{GREEN}25")),
                            ], spacing=8)),
                    ], spacing=0),
                    bgcolor=BG2, border_radius=16,
                    border=ft.border.all(1, BORDER2),
                    shadow=ft.BoxShadow(blur_radius=20, color="#00000055"),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS),

                ft.Container(height=14),

                # ── Card iteraciones ──────────────────────────────────────
                ft.Container(ref=iter_card, visible=False,
                    content=ft.Column([
                        ft.Container(height=3,
                            gradient=ft.LinearGradient([BLUE, BLUE_L, BLUE],
                                begin=ft.Alignment(-1,0), end=ft.Alignment(1,0)),
                            border_radius=ft.border_radius.only(
                                top_left=16, top_right=16)),
                        ft.Container(padding=16,
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.TABLE_CHART_OUTLINED,
                                                        color=BLUE_L, size=16),
                                        bgcolor=f"{BLUE_L}18", border_radius=8,
                                        padding=7,
                                        border=ft.border.all(1,f"{BLUE_L}30")),
                                    ft.Column([
                                        ft.Text("Iteraciones Paso a Paso",
                                                size=14, weight=ft.FontWeight.BOLD,
                                                color=TXT),
                                        ft.Text("Seguimiento del algoritmo",
                                                size=10, color=TXT3),
                                    ], spacing=0),
                                ], spacing=10),

                                ft.Container(height=4),
                                tabs_row,
                                ft.Container(height=4),

                                # Prev / counter / Next
                                ft.Row([
                                    ft.ElevatedButton(
                                        content=ft.Row([
                                            ft.Icon(ft.Icons.CHEVRON_LEFT,
                                                    size=15, color=TXT2),
                                            ft.Text("Ant.", size=12, color=TXT2),
                                        ], spacing=4, tight=True),
                                        style=ft.ButtonStyle(
                                            bgcolor=BG5,
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            side=ft.BorderSide(1, BORDER2),
                                            padding=ft.padding.symmetric(
                                                horizontal=12, vertical=9)),
                                        on_click=lambda _: render_tabla(
                                            max(0, state["iter_actual"]-1))),
                                    ft.Container(
                                        content=counter_txt, bgcolor=BG5,
                                        border_radius=10, padding=ft.padding.symmetric(
                                            horizontal=14, vertical=9),
                                        border=ft.border.all(1, BORDER2)),
                                    ft.ElevatedButton(
                                        content=ft.Row([
                                            ft.Text("Sig.", size=12, color=TXT2),
                                            ft.Icon(ft.Icons.CHEVRON_RIGHT,
                                                    size=15, color=TXT2),
                                        ], spacing=4, tight=True),
                                        style=ft.ButtonStyle(
                                            bgcolor=BG5,
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            side=ft.BorderSide(1, BORDER2),
                                            padding=ft.padding.symmetric(
                                                horizontal=12, vertical=9)),
                                        on_click=lambda _: render_tabla(
                                            min(len(state["iteraciones"])-1,
                                                state["iter_actual"]+1))),
                                ], spacing=8),

                                ft.Divider(color=BORDER),

                                ft.Container(
                                    content=desc_txt, bgcolor=BG4,
                                    border_radius=10, padding=10,
                                    border=ft.border.only(
                                        left=ft.border.BorderSide(3, RED))),
                                nota_box,
                                ft.Container(
                                    content=tabla_col,
                                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
                            ], spacing=8)),
                    ], spacing=0),
                    bgcolor=BG2, border_radius=16,
                    border=ft.border.all(1, BORDER2),
                    shadow=ft.BoxShadow(blur_radius=20, color="#00000055"),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS),

                ft.Container(height=24),
            ], spacing=0)),
    )

    build_form()
    load_example()

ft.app(target=main, assets_dir="assets")
