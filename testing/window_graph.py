import flet as ft
import random
import time
import threading

class ChartApp:
    def __init__(self):
        self.is_running = False
        self.data_points = {
            'temperature': [],
            'humidity': [],
            'pressure': []
        }
        self.max_points = 20  # Maximum number of points to display
        self.current_x = 0
        
    def generate_random_data(self):
        """Generate random values for the three variables"""
        temperature = random.uniform(20, 35)  # Temperature: 20-35°C
        humidity = random.uniform(30, 80)     # Humidity: 30-80%
        pressure = random.uniform(950, 1050)  # Pressure: 950-1050 hPa
        
        return temperature, humidity, pressure
    
    def add_data_point(self, temp, hum, press):
        """Add new data points and maintain maximum points limit"""
        self.data_points['temperature'].append(ft.LineChartDataPoint(self.current_x, temp))
        self.data_points['humidity'].append(ft.LineChartDataPoint(self.current_x, hum))
        self.data_points['pressure'].append(ft.LineChartDataPoint(self.current_x, press/10))  # Scale pressure for visibility
        
        # Remove old points if we exceed the maximum
        if len(self.data_points['temperature']) > self.max_points:
            for key in self.data_points:
                self.data_points[key].pop(0)
        
        self.current_x += 1
    
    def create_chart_data(self):
        """Create the chart data series"""
        return [
            ft.LineChartData(
                data_points=self.data_points['temperature'].copy(),
                stroke_width=3,
                color=ft.Colors.RED,
                curved=True,
                stroke_cap_round=True,
            ),
            ft.LineChartData(
                data_points=self.data_points['humidity'].copy(),
                stroke_width=3,
                color=ft.Colors.BLUE,
                curved=True,
                stroke_cap_round=True,
            ),
            ft.LineChartData(
                data_points=self.data_points['pressure'].copy(),
                stroke_width=3,
                color=ft.Colors.GREEN,
                curved=True,
                stroke_cap_round=True,
            ),
        ]

def main(page: ft.Page):
    page.title = "Gráfico en Tiempo Real - Tres Variables"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    app = ChartApp()
    
    # Create initial data points
    for i in range(5):
        temp, hum, press = app.generate_random_data()
        app.add_data_point(temp, hum, press)
    
    # Create the chart
    chart = ft.LineChart(
        data_series=app.create_chart_data(),
        border=ft.border.all(2, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        horizontal_grid_lines=ft.ChartGridLines(
            interval=10, 
            color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE), 
            width=1
        ),
        vertical_grid_lines=ft.ChartGridLines(
            interval=2, 
            color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE), 
            width=1
        ),
        left_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(value=20, label=ft.Text("20", size=12)),
                ft.ChartAxisLabel(value=40, label=ft.Text("40", size=12)),
                ft.ChartAxisLabel(value=60, label=ft.Text("60", size=12)),
                ft.ChartAxisLabel(value=80, label=ft.Text("80", size=12)),
                ft.ChartAxisLabel(value=100, label=ft.Text("100", size=12)),
            ],
            labels_size=40,
        ),
        bottom_axis=ft.ChartAxis(
            labels_size=32,
        ),
        tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLUE_GREY),
        min_y=0,
        max_y=110,
        interactive=True,
        expand=True,
    )
    
    # Status indicators
    status_text = ft.Text("Estado: Detenido", size=16)
    temp_text = ft.Text("Temperatura: -- °C", size=14, color=ft.Colors.RED)
    hum_text = ft.Text("Humedad: -- %", size=14, color=ft.Colors.BLUE)
    press_text = ft.Text("Presión: -- hPa", size=14, color=ft.Colors.GREEN)
    
    def update_chart():
        """Update chart with new data"""
        while app.is_running:
            temp, hum, press = app.generate_random_data()
            app.add_data_point(temp, hum, press)
            
            # Update chart data
            chart.data_series = app.create_chart_data()
            
            # Update chart x-axis range to show recent data
            if len(app.data_points['temperature']) >= app.max_points:
                chart.min_x = app.current_x - app.max_points
                chart.max_x = app.current_x
            else:
                chart.min_x = 0
                chart.max_x = max(10, app.current_x)
            
            # Update status texts
            temp_text.value = f"Temperatura: {temp:.1f} °C"
            hum_text.value = f"Humedad: {hum:.1f} %"
            press_text.value = f"Presión: {press:.1f} hPa"
            
            # Update UI
            page.update()
            time.sleep(1)  # Update every second
    
    def start_stop_clicked(e):
        """Toggle data generation"""
        if not app.is_running:
            app.is_running = True
            status_text.value = "Estado: Ejecutándose"
            start_stop_btn.text = "Detener"
            start_stop_btn.icon = ft.Icons.STOP
            
            # Start update thread
            threading.Thread(target=update_chart, daemon=True).start()
        else:
            app.is_running = False
            status_text.value = "Estado: Detenido"
            start_stop_btn.text = "Iniciar"
            start_stop_btn.icon = ft.Icons.PLAY_ARROW
        
        page.update()
    
    def clear_data_clicked(e):
        """Clear all data points"""
        app.data_points = {'temperature': [], 'humidity': [], 'pressure': []}
        app.current_x = 0
        chart.data_series = app.create_chart_data()
        chart.min_x = 0
        chart.max_x = 10
        
        temp_text.value = "Temperatura: -- °C"
        hum_text.value = "Humedad: -- %"
        press_text.value = "Presión: -- hPa"
        
        page.update()
    
    # Control buttons
    start_stop_btn = ft.ElevatedButton(
        text="Iniciar",
        icon=ft.Icons.PLAY_ARROW,
        on_click=start_stop_clicked,
    )
    
    clear_btn = ft.ElevatedButton(
        text="Limpiar",
        icon=ft.Icons.CLEAR,
        on_click=clear_data_clicked,
    )
    
    # Legend
    legend = ft.Row([
        ft.Container(
            content=ft.Row([
                ft.Container(width=20, height=3, bgcolor=ft.Colors.RED),
                ft.Text("Temperatura (°C)", size=12)
            ]),
        ),
        ft.Container(
            content=ft.Row([
                ft.Container(width=20, height=3, bgcolor=ft.Colors.BLUE),
                ft.Text("Humedad (%)", size=12)
            ]),
        ),
        ft.Container(
            content=ft.Row([
                ft.Container(width=20, height=3, bgcolor=ft.Colors.GREEN),
                ft.Text("Presión (hPa/10)", size=12)
            ]),
        ),
    ])
    
    # Layout
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("Monitor de Variables en Tiempo Real", size=24, weight=ft.FontWeight.BOLD),
                
                ft.Row([
                    start_stop_btn,
                    clear_btn,
                    status_text,
                ], alignment=ft.MainAxisAlignment.START),
                
                ft.Row([
                    temp_text,
                    hum_text,
                    press_text,
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                
                legend,
                
                ft.Container(
                    content=chart,
                    height=400,
                    padding=ft.padding.all(10),
                ),
            ]),
            padding=ft.padding.all(20),
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
