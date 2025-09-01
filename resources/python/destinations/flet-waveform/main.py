import flet as ft
import os
from datetime import datetime
from shared_quix_service import shared_quix_service
from quix_timeseries_plot import QuixTimeseriesPlot

#from dotenv import load_dotenv
#load_dotenv(".env")


class WaveformViewer:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Real-time Waveform Viewer"
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        
        # Add page event handlers to handle tab duplication issues
        self.page.on_window_event = self.handle_window_event
        
        # Unique instance identifier for debugging
        import uuid
        self.instance_id = str(uuid.uuid4())[:8]
        print(f"Creating WaveformViewer instance: {self.instance_id}")
        
        # Status indicators
        self.connection_status = ft.Text("Disconnected", color=ft.Colors.RED)
        self.last_update = ft.Text("No data received")
        self.message_count = ft.Text("Messages: 0")
        
        # Create timeseries plots
        self.temperature_plot = QuixTimeseriesPlot(
            title="CPU usage",
            y_axis_label="Usage",
            units="%",
            height=300,
            update_callback=self.on_data_updated,
            page_update_callback=self.page.update
        )
        
        # Add multiple series with distinct colors
        self.temperature_plot.add_series("usage_user", ft.Colors.ORANGE, 2)
        self.temperature_plot.add_series("usage_system", ft.Colors.BLUE, 2)
        
        self.setup_ui()
        self.start_services()
  
    def on_data_updated(self, total_points, last_update_time):
        """Callback when new data is added to the plot"""
        try:
            self.message_count.value = f"Data points: {total_points}"
            self.last_update.value = f"Last update: {last_update_time}"
            if self.page:
                self.page.update()
        except Exception as e:
            if "disconnected" in str(e).lower():
                print(f"Instance {self.instance_id} disconnected, cleaning up...")
                self.cleanup()
            else:
                print(f"Error updating data stats in instance {self.instance_id}: {e}")
    
    
    def handle_kafka_status(self, status, color):
        """Handle Kafka connection status updates"""
        try:
            self.connection_status.value = status
            self.connection_status.color = getattr(ft.Colors, color)
            if self.page:
                self.page.update()
        except Exception as e:
            if "disconnected" in str(e).lower():
                print(f"Instance {self.instance_id} disconnected, cleaning up...")
                self.cleanup()
            else:
                print(f"Error updating status in instance {self.instance_id}: {e}")
    
    def start_services(self):
        """Start the shared Quix service"""
        # Get topic name from environment variable
        topic_name = os.environ["input"]

        print(topic_name)
        
        # Set topic and add callbacks to shared service
        shared_quix_service.set_topic(topic_name)
        shared_quix_service.add_status_callback(self.handle_kafka_status)
        print(f"Instance {self.instance_id} registered callbacks")
        
        # Start the shared service (only starts once across all instances)
        shared_quix_service.start()
        
        # Update initial status from shared service
        status_info = shared_quix_service.get_status()
        if status_info['status'] == "Connected":
            self.handle_kafka_status("Connected", "GREEN")
        else:
            self.handle_kafka_status(status_info['status'], "RED")
    
    def handle_window_event(self, e):
        """Handle window events like focus to re-enable updates"""
        if e.data == "focus":
            print(f"Instance {self.instance_id} gained focus - forcing update")
            try:
                # Force a page update when tab gains focus
                self.page.update()
            except Exception as ex:
                print(f"Error on focus update: {ex}")
    
    def cleanup(self):
        """Clean up callbacks when closing the app instance"""
        if not hasattr(self, '_cleaned_up'):
            print(f"Cleaning up instance {self.instance_id}")
            shared_quix_service.remove_status_callback(self.handle_kafka_status)
            self._cleaned_up = True
    
    def setup_ui(self):
        """Setup the user interface"""
        self.page.add(
            ft.Container(
                content=ft.Text("Real-time Waveform Viewer", style=ft.TextThemeStyle.HEADLINE_LARGE),
                margin=ft.margin.only(bottom=20)
            ),
            
            # Status panel
            ft.Container(
                content=ft.Column([
                    ft.Text("Connection Status", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.Row([
                        self.connection_status,
                        ft.Text(" | "),
                        self.last_update,
                        ft.Text(" | "),
                        self.message_count
                    ])
                ]),
                bgcolor=ft.Colors.GREY_900,
                padding=20,
                border_radius=10,
                margin=ft.margin.only(bottom=20)
            ),
            
           
            # Temperature plot using the custom component
            self.temperature_plot.get_container()
        )


def main(page: ft.Page):
    WaveformViewer(page)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=80, host="0.0.0.0", assets_dir="/app/state")