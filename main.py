import flet as ft
import httpx
import asyncio
from typing import List

BACKEND_URL = "http://192.168.137.37:8080"

# ── Colores ───────────────────────────────────────────────────────────────────
BG       = "#070a10"
BG2      = "#0d1119"
BG3      = "#131824"
BG4      = "#191f2e"
BG5      = "#1e2538"
BORDER   = "#1e2840"
BORDER2  = "#2d3a55"
RED      = "#C0392B"
RED_L    = "#E74C3C"
GOLD     = "#F1C40F"
GOLD_D   = "#D4AC0D"
BLUE     = "#2471A3"
BLUE_L   = "#3498DB"
GREEN    = "#27AE60"
ORANGE   = "#E67E22"
TXT      = "#dde3f0"
TXT2     = "#7a89a8"
TXT3     = "#3d4d6a"
NEG      = "#F1948A"
ROW_COLORS = [RED_L, BLUE_L, GREEN, GOLD_D]

def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9: return str(int(round(v)))
    for d in range(1, 33):
        n = round(v * d)
        if abs(n / d - v) < 1e-9: return f"{n}/{d}"
    return f"{v:.4f}"

# ── Helpers UI ────────────────────────────────────────────────────────────────

def card(content, **kwargs):
    return ft.Container(
        content=content, bgcolor=BG2, border_radius=16, padding=20,
        border=ft.border.all(1, BORDER2),
        shadow=ft.BoxShadow(blur_radius=24, color="#00000066", offset=ft.Offset(0,4)),
        **kwargs,
    )

def section_title(text):
    return ft.Row([
        ft.Container(width=3, height=14,
            gradient=ft.LinearGradient(
                [RED, GOLD],
                begin=ft.Alignment(0,-1), end=ft.Alignment(0,1)),
            border_radius=2),
        ft.Text(text.upper(), size=11, weight=ft.FontWeight.BOLD,
                color=TXT2, letter_spacing=1.5),
    ], spacing=8)

def styled_field(value="", width=72):
    return ft.TextField(
        value=value, width=width, text_align=ft.TextAlign.CENTER,
        text_size=14, color=TXT, bgcolor=BG4,
        border_color=BORDER2, focused_border_color=RED_L,
        border_radius=10,
        content_padding=ft.padding.symmetric(horizontal=8, vertical=10),
        keyboard_type=ft.KeyboardType.NUMBER,
    )

def badge_pill(text, color, bg):
    return ft.Container(
        content=ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=color),
        bgcolor=bg, border_radius=999,
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        border=ft.border.all(1, f"{color}40"),
    )

def divider_line(color=RED):
    return ft.Container(
        height=1,
        gradient=ft.LinearGradient([color,"transparent"],
            begin=ft.Alignment(-1,0), end=ft.Alignment(1,0)),
        margin=ft.margin.symmetric(vertical=14), opacity=0.5,
    )

def main(page: ft.Page):
    page.title = "Simplex — Universidad de Panamá"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # ── Estado ────────────────────────────────────────────────────────────────
    state = {
        "n_vars": 2, "n_cons": 2,
        "iteraciones": [], "iter_actual": 0,
    }
    obj_fields: List[ft.TextField] = []
    con_fields: List[List[ft.TextField]] = []
    rhs_fields: List[ft.TextField] = []

    # ── Refs ──────────────────────────────────────────────────────────────────
    form_col        = ft.Column(spacing=10)
    result_card     = ft.Ref[ft.Container]()
    iters_card      = ft.Ref[ft.Container]()
    tabla_col       = ft.Column(scroll=ft.ScrollMode.AUTO)
    iter_tabs_row   = ft.Row(spacing=6, wrap=True)
    desc_txt        = ft.Text("", size=13, weight=ft.FontWeight.BOLD, color=TXT)
    nota_container  = ft.Container(visible=False, bgcolor=f"{BLUE}18",
                                   border_radius=10, padding=12,
                                   border=ft.border.all(1, f"{BLUE_L}30"))
    nota_txt        = ft.Text("", size=12, color=TXT2)
    z_txt           = ft.Text("", size=32, weight=ft.FontWeight.BOLD, color=GOLD,
                               text_align=ft.TextAlign.CENTER)
    vars_row        = ft.Row(spacing=8, wrap=True)
    holguras_row    = ft.Row(spacing=10, wrap=True)
    msg_txt         = ft.Text("", size=13, color=GREEN)
    error_box       = ft.Container(visible=False, bgcolor=f"{NEG}12", border_radius=12,
                                   padding=12, border=ft.border.all(1, f"{NEG}30"))
    error_txt       = ft.Text("", size=13, color=NEG)
    loading_ring    = ft.ProgressRing(visible=False, color=RED,
                                       stroke_width=2, width=24, height=24)
    counter_txt     = ft.Text("0 / 0", size=13, weight=ft.FontWeight.BOLD, color=TXT2)

    nota_container.content = ft.Row([
        ft.Container(width=3, bgcolor=BLUE_L, border_radius=2),
        nota_txt,
    ], spacing=10)
    error_box.content = ft.Row([
        ft.Icon(ft.Icons.ERROR_OUTLINE, color=NEG, size=16), error_txt
    ], spacing=8)

    # ── Build form ────────────────────────────────────────────────────────────
    def build_form():
        nonlocal obj_fields, con_fields, rhs_fields
        nv = state["n_vars"]; nc = state["n_cons"]
        obj_fields = [styled_field() for _ in range(4)]
        con_fields = [[styled_field() for _ in range(4)] for _ in range(4)]
        rhs_fields = [styled_field() for _ in range(4)]
        rows = [section_title("Función objetivo")]
        obj_row = [ft.Text("Z =", size=16, weight=ft.FontWeight.BOLD, color=GOLD)]
        for j in range(nv):
            if j > 0: obj_row.append(ft.Text("+", size=14, color=TXT2))
            obj_row += [obj_fields[j], ft.Text(f"x{j+1}", size=13, color=TXT2)]
        rows.append(ft.Row(obj_row, spacing=6, wrap=True))
        rows.append(divider_line(GOLD))
        rows.append(section_title("Restricciones"))
        for i in range(nc):
            c = ROW_COLORS[i % 4]
            r = [ft.Container(
                    content=ft.Text(f"R{i+1}", size=11, weight=ft.FontWeight.BOLD, color=c),
                    bgcolor=f"{c}20", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border=ft.border.all(1, f"{c}40"))]
            for j in range(nv):
                if j > 0: r.append(ft.Text("+", size=14, color=TXT2))
                r += [con_fields[i][j], ft.Text(f"x{j+1}", size=13, color=TXT2)]
            r += [ft.Text("≤", size=16, weight=ft.FontWeight.BOLD, color=GOLD), rhs_fields[i]]
            rows.append(ft.Row(r, spacing=6, wrap=True))
        form_col.controls = rows
        page.update()

    def load_example(_=None):
        state["n_vars"] = 2; state["n_cons"] = 2
        build_form()
        obj_fields[0].value="50"; obj_fields[1].value="80"
        con_fields[0][0].value="1"; con_fields[0][1].value="2"; rhs_fields[0].value="120"
        con_fields[1][0].value="1"; con_fields[1][1].value="1"; rhs_fields[1].value="90"
        clear_result(); page.update()

    def clear_result(_=None):
        state["iteraciones"] = []; state["iter_actual"] = 0
        if result_card.current: result_card.current.visible = False
        if iters_card.current: iters_card.current.visible = False
        show_error(""); page.update()

    def show_error(msg):
        error_box.visible = bool(msg); error_txt.value = msg; page.update()

    # ── Render tabla ──────────────────────────────────────────────────────────
    def render_tabla(idx: int):
        state["iter_actual"] = idx
        it    = state["iteraciones"][idx]
        total = len(state["iteraciones"])

        desc_txt.value = it["descripcion"]
        nota = it.get("nota_pivote") or ""
        nota_txt.value = nota; nota_container.visible = bool(nota)
        counter_txt.value = f"{idx} / {total-1}"

        piv_col = it["columna_pivote"] if it["columna_pivote"] is not None else -1
        piv_row = it["fila_pivote"]    if it["fila_pivote"]    is not None else -1
        cols    = it["nombres_columnas"]
        base    = it["base"]
        tabla   = it["tabla"]

        # Tabla DataTable
        header = [ft.DataColumn(
            ft.Text("Base", size=11, weight=ft.FontWeight.BOLD, color=TXT3, italic=True)
        )]
        for j, col in enumerate(cols):
            header.append(ft.DataColumn(ft.Container(
                content=ft.Text(col, size=11, weight=ft.FontWeight.BOLD,
                                color=BLUE_L if j==piv_col else TXT3),
                bgcolor=f"{BLUE_L}30" if j==piv_col else "transparent",
                border_radius=6, padding=ft.padding.symmetric(horizontal=6, vertical=2),
            )))

        data_rows = []
        for i, fila in enumerate(tabla):
            base_name = "Z" if i==0 else base[i-1]
            cells = [ft.DataCell(ft.Text(base_name, size=13,
                                          weight=ft.FontWeight.BOLD,
                                          color=GOLD if i==0 else RED_L))]
            for j, val in enumerate(fila):
                is_piv  = (j==piv_col and i==piv_row)
                fval    = _fmt(val)
                is_neg  = fval.startswith("-") and i==0
                txt_c   = "white" if is_piv else (NEG if is_neg else TXT)
                cell_bg = (BLUE_L if is_piv else
                           (f"{BLUE}40" if j==piv_col else
                            (f"{RED}30" if i==piv_row else "transparent")))
                cells.append(ft.DataCell(ft.Container(
                    content=ft.Text(fval, size=13, color=txt_c,
                                    weight=ft.FontWeight.BOLD if is_piv else ft.FontWeight.NORMAL),
                    bgcolor=cell_bg, border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )))
            row_bg = f"{GOLD}08" if i==0 else f"{RED}08"
            data_rows.append(ft.DataRow(cells=cells,
                                        color=ft.MaterialStatePropertyAll(row_bg)))

        tabla_col.controls = [
            ft.DataTable(
                columns=header, rows=data_rows,
                bgcolor=BG3, border=ft.border.all(1, BORDER),
                border_radius=12,
                heading_row_color=ft.MaterialStatePropertyAll(BG4),
                data_row_min_height=40, column_spacing=16,
                horizontal_lines=ft.border.BorderSide(1, BORDER),
                vertical_lines=ft.border.BorderSide(1, BORDER),
            )
        ]

        # Pills
        tabs = []
        for k in range(total):
            desc_k = state["iteraciones"][k]["descripcion"]
            lbl = ("I" if k==0 else "✓" if k==total-1 else
                   "A" if "Paso A" in desc_k else
                   "B" if "Paso B" in desc_k else
                   "C" if "Paso C" in desc_k else str(k))
            is_act = k == idx
            kk = k
            tabs.append(ft.Container(
                content=ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD,
                                color="white" if is_act else TXT2,
                                text_align=ft.TextAlign.CENTER),
                width=34, height=34, border_radius=17,
                bgcolor=RED if is_act else BG5,
                border=ft.border.all(2 if is_act else 1,
                                     RED_L if is_act else BORDER2),
                shadow=ft.BoxShadow(blur_radius=12,
                                    color=f"{RED}60" if is_act else "transparent"),
                alignment=ft.alignment.center,
                on_click=lambda e, ki=kk: render_tabla(ki), ink=True,
            ))
        iter_tabs_row.controls = tabs
        page.update()

    # ── Resolver ──────────────────────────────────────────────────────────────
    async def resolver_async(_=None):
        show_error(""); loading_ring.visible = True; page.update()
        try:
            nv = state["n_vars"]; nc = state["n_cons"]
            obj_vals = []
            for j in range(nv):
                v = obj_fields[j].value.strip()
                if not v: show_error(f"Falta coeficiente en Z para x{j+1}"); return
                obj_vals.append(float(v))
            A = []
            for i in range(nc):
                row = []
                for j in range(nv):
                    v = con_fields[i][j].value.strip()
                    if not v: show_error(f"Falta coef. en R{i+1}, x{j+1}"); return
                    row.append(float(v))
                A.append(row)
            b_vals = []
            for i in range(nc):
                v = rhs_fields[i].value.strip()
                if not v: show_error(f"Falta RHS en R{i+1}"); return
                b_vals.append(float(v))

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(f"{BACKEND_URL}/simplex",
                    json={"objetivo":obj_vals,"restricciones":A,"rhs":b_vals})
                data = resp.json()

            if not data.get("exito"):
                show_error(data.get("mensaje","Error")); return

            state["iteraciones"] = data["iteraciones"]

            # Z
            z_txt.value = str(data["z_optimo"])

            # Variables
            vchips = []
            for j, val in enumerate(data["variables_decision"]):
                vchips.append(ft.Container(
                    content=ft.Column([
                        ft.Text(f"x{j+1}", size=11, color=TXT3, text_align=ft.TextAlign.CENTER),
                        ft.Text(str(val), size=22, weight=ft.FontWeight.BOLD,
                                color=RED_L, text_align=ft.TextAlign.CENTER),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=f"{RED}18", border_radius=14,
                    padding=ft.padding.symmetric(horizontal=20, vertical=14),
                    border=ft.border.all(1, f"{RED}30"), min_width=100,
                ))
            vars_row.controls = vchips

            # Holguras
            hchips = []
            for j, val in enumerate(data["holguras"]):
                is_act = abs(val) < 1e-9
                c = ORANGE if is_act else BLUE_L
                hchips.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"S{j+1}", size=12,
                                                weight=ft.FontWeight.BOLD, color=c),
                                bgcolor=f"{c}20", border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                            ft.Text("=", size=13, color=TXT3),
                            ft.Text(str(val), size=16, weight=ft.FontWeight.BOLD, color=TXT),
                        ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row([
                            ft.Container(width=6, height=6, border_radius=3, bgcolor=c),
                            ft.Text("Activa" if is_act else "Sobrante", size=11, color=c),
                        ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                    ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=BG4, border_radius=12,
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border=ft.border.all(1, f"{c}30"),
                ))
            holguras_row.controls = hchips
            msg_txt.value = data.get("mensaje","")

            result_card.current.visible = True
            iters_card.current.visible = True
            render_tabla(0)

        except httpx.ConnectError:
            show_error("No se pudo conectar al backend. Verifica la IP y puerto 8080.")
        except Exception as e:
            show_error(f"Error: {e}")
        finally:
            loading_ring.visible = False; page.update()

    def resolver(e): asyncio.create_task(resolver_async(e))

    def change_vars(e): state["n_vars"]=int(e.control.value); build_form()
    def change_cons(e): state["n_cons"]=int(e.control.value); build_form()

    # ── Layout ────────────────────────────────────────────────────────────────
    page.add(
        # Navbar
        ft.Container(
            content=ft.Row([
                ft.Image(src="/UP-logo.png", width=44, height=44, fit=ft.ImageFit.CONTAIN),
                ft.Container(width=1, height=36, bgcolor=BORDER2),
                ft.Column([
                    ft.Text("Método Simplex", size=16, weight=ft.FontWeight.BOLD, color=TXT),
                    ft.Text("Universidad de Panamá · IO", size=11, color=TXT3),
                ], spacing=0, expand=True),
                badge_pill("Maximización", GOLD, f"{GOLD}18"),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=BG2, padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border=ft.border.only(bottom=ft.border.BorderSide(1, BORDER2)),
            shadow=ft.BoxShadow(blur_radius=20, color="#00000080"),
        ),

        ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
            ft.Container(padding=16, content=ft.Column([

                # ── Formulario ────────────────────────────────────────────
                card(ft.Column([
                    # Dimensiones
                    ft.Row([
                        ft.Column([
                            ft.Text("Variables", size=11, color=TXT3),
                            ft.Dropdown(value="2", width=90, bgcolor=BG4, color=TXT,
                                border_color=BORDER2, focused_border_color=RED_L,
                                border_radius=10, on_change=change_vars,
                                options=[ft.dropdown.Option(str(i)) for i in [2,3,4]]),
                        ], spacing=4),
                        ft.Column([
                            ft.Text("Restricciones", size=11, color=TXT3),
                            ft.Dropdown(value="2", width=120, bgcolor=BG4, color=TXT,
                                border_color=BORDER2, focused_border_color=RED_L,
                                border_radius=10, on_change=change_cons,
                                options=[ft.dropdown.Option(str(i)) for i in [2,3,4]]),
                        ], spacing=4),
                        ft.Column([
                            ft.Text("No negatividades", size=11, color=TXT3),
                            ft.Container(
                                content=ft.Text("x ≥ 0  implícito", size=12,
                                                weight=ft.FontWeight.BOLD, color=GREEN),
                                bgcolor=f"{GREEN}18", border_radius=10, padding=8,
                                border=ft.border.all(1, f"{GREEN}30")),
                        ], spacing=4),
                    ], spacing=14, wrap=True),

                    divider_line(RED),
                    form_col,
                    divider_line(RED),

                    # Botones
                    ft.Row([
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, size=16, color="white"),
                                ft.Text("Resolver", size=13, weight=ft.FontWeight.BOLD, color="white"),
                            ], spacing=8, tight=True),
                            style=ft.ButtonStyle(
                                bgcolor=RED, overlay_color=f"{RED}CC",
                                shape=ft.RoundedRectangleBorder(radius=12),
                                shadow_color=f"{RED}80", elevation=8,
                                padding=ft.padding.symmetric(horizontal=22, vertical=12)),
                            on_click=resolver),
                        ft.OutlinedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.BOOK_OUTLINED, size=14, color=TXT2),
                                ft.Text("Ejemplo del profe", size=13, color=TXT2),
                            ], spacing=8, tight=True),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, BORDER2),
                                shape=ft.RoundedRectangleBorder(radius=12),
                                overlay_color=BG4,
                                padding=ft.padding.symmetric(horizontal=16, vertical=12)),
                            on_click=load_example),
                        ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color=TXT3,
                            on_click=clear_result,
                            style=ft.ButtonStyle(
                                bgcolor=BG5,
                                shape=ft.RoundedRectangleBorder(radius=12),
                                side=ft.BorderSide(1, BORDER))),
                    ], spacing=10, wrap=True),

                    loading_ring,
                    error_box,
                ], spacing=10)),

                ft.Container(height=16),

                # ── Solución óptima ───────────────────────────────────────
                ft.Container(ref=result_card, visible=False,
                    content=ft.Column([
                        ft.Container(height=3, gradient=ft.LinearGradient(
                            [GOLD, GREEN, GOLD],
                            begin=ft.Alignment(-1,0), end=ft.Alignment(1,0)),
                            border_radius=ft.border_radius.only(top_left=16,top_right=16)),
                        ft.Container(padding=20, content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Icon(ft.Icons.EMOJI_EVENTS, color=GOLD, size=18),
                                    bgcolor=f"{GOLD}18", border_radius=10, padding=8,
                                    border=ft.border.all(1, f"{GOLD}30")),
                                ft.Column([
                                    ft.Text("Solución Óptima", size=16,
                                            weight=ft.FontWeight.BOLD, color=TXT),
                                    ft.Text("Valor máximo encontrado", size=11, color=TXT3),
                                ], spacing=0),
                                ft.Container(expand=True),
                                badge_pill("ÓPTIMO", GREEN, f"{GREEN}18"),
                            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(height=8),
                            ft.Row([
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text("Z máximo", size=11, color=TXT3,
                                                text_align=ft.TextAlign.CENTER),
                                        z_txt,
                                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                    bgcolor=f"{GOLD}10", border_radius=14, padding=16,
                                    border=ft.border.all(1, f"{GOLD}25"), min_width=130),
                                vars_row,
                            ], spacing=12, wrap=True,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Divider(color=BORDER, height=24),
                            ft.Text("Variables de Holgura", size=11, color=TXT3,
                                    letter_spacing=1.5),
                            holguras_row,
                            ft.Container(height=4),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE,
                                            color=GREEN, size=15),
                                    msg_txt,
                                ], spacing=8),
                                bgcolor=f"{GREEN}12", border_radius=12, padding=12,
                                border=ft.border.all(1, f"{GREEN}25")),
                        ], spacing=10)),
                    ], spacing=0),
                    bgcolor=BG2, border_radius=16,
                    border=ft.border.all(1, BORDER2),
                    shadow=ft.BoxShadow(blur_radius=24, color="#00000066"),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS),

                ft.Container(height=16),

                # ── Iteraciones ───────────────────────────────────────────
                ft.Container(ref=iters_card, visible=False,
                    content=ft.Column([
                        ft.Container(height=3, gradient=ft.LinearGradient(
                            [BLUE, BLUE_L, BLUE],
                            begin=ft.Alignment(-1,0), end=ft.Alignment(1,0)),
                            border_radius=ft.border_radius.only(top_left=16,top_right=16)),
                        ft.Container(padding=20, content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Icon(ft.Icons.TABLE_CHART_OUTLINED,
                                                    color=BLUE_L, size=17),
                                    bgcolor=f"{BLUE_L}18", border_radius=10, padding=8,
                                    border=ft.border.all(1, f"{BLUE_L}30")),
                                ft.Column([
                                    ft.Text("Iteraciones Paso a Paso", size=15,
                                            weight=ft.FontWeight.BOLD, color=TXT),
                                    ft.Text("Seguimiento completo del algoritmo",
                                            size=11, color=TXT3),
                                ], spacing=0),
                            ], spacing=12),
                            ft.Container(height=6),
                            iter_tabs_row,
                            ft.Container(height=4),
                            ft.Row([
                                ft.ElevatedButton(
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.CHEVRON_LEFT, size=16, color=TXT2),
                                        ft.Text("Anterior", size=12, color=TXT2),
                                    ], spacing=4, tight=True),
                                    style=ft.ButtonStyle(
                                        bgcolor=BG5,
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        side=ft.BorderSide(1, BORDER2),
                                        padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                                    on_click=lambda _: render_tabla(
                                        max(0, state["iter_actual"]-1))),
                                ft.Container(
                                    content=counter_txt, bgcolor=BG5, border_radius=10,
                                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                                    border=ft.border.all(1, BORDER2)),
                                ft.ElevatedButton(
                                    content=ft.Row([
                                        ft.Text("Siguiente", size=12, color=TXT2),
                                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=TXT2),
                                    ], spacing=4, tight=True),
                                    style=ft.ButtonStyle(
                                        bgcolor=BG5,
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        side=ft.BorderSide(1, BORDER2),
                                        padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                                    on_click=lambda _: render_tabla(
                                        min(len(state["iteraciones"])-1,
                                            state["iter_actual"]+1))),
                            ], spacing=8),
                            ft.Divider(color=BORDER),
                            ft.Container(
                                content=desc_txt, bgcolor=BG4, border_radius=10, padding=12,
                                border=ft.border.only(left=ft.border.BorderSide(3, RED))),
                            nota_container,
                            ft.Container(
                                content=tabla_col,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
                        ], spacing=10)),
                    ], spacing=0),
                    bgcolor=BG2, border_radius=16,
                    border=ft.border.all(1, BORDER2),
                    shadow=ft.BoxShadow(blur_radius=24, color="#00000066"),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS),

                ft.Container(height=24),
            ], spacing=0)),
        ]),
    )

    build_form()
    load_example()

ft.app(target=main, assets_dir="assets")
