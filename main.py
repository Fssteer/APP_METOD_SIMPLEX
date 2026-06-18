import flet as ft

def main(page: ft.Page):
    page.title = "Simplex IO"
    page.bgcolor = "#070a10"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16

    page.add(
        ft.Text("Método Simplex", size=24, weight=ft.FontWeight.BOLD, color="#E74C3C"),
        ft.Text("Universidad de Panamá", size=14, color="#7a89a8"),
        ft.ElevatedButton("Probar", on_click=lambda _: print("ok")),
    )

ft.app(target=main)
