import flet as ft

def main(page: ft.Page):
    page.title = "Simplex IO"
    page.bgcolor = "#070a10"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    page.add(
        ft.Text("Método Simplex", size=24,
                weight=ft.FontWeight.BOLD, color="#E74C3C"),
        ft.Text("Universidad de Panamá", size=14, color="#7a89a8"),
        ft.Container(height=20),
        ft.TextField(label="Z: coef x1", width=120,
                     bgcolor="#191f2e", color="white",
                     border_color="#2d3a55", border_radius=10),
        ft.Container(height=10),
        ft.ElevatedButton(
            "Resolver",
            style=ft.ButtonStyle(bgcolor="#C0392B"),
            on_click=lambda _: page.add(ft.Text("✓ Funciona!", color="#27AE60"))
        ),
    )

ft.app(target=main, assets_dir="assets")
