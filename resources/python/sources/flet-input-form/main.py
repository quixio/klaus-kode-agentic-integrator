"""Manufacturing Settings Input Form

A web-based application for inputting and submitting manufacturing machine
settings to a Kafka topic using Quix Streams. Built with Flet for the UI.
"""

import flet as ft
import os
from datetime import datetime
from shared_quix_service import shared_quix_service

#from dotenv import load_dotenv
#load_dotenv(".env")

class ManufacturingSettingsForm:
    def __init__(self, page: ft.Page):
        """Initialize the manufacturing settings form.
        
        Args:
            page: The Flet page object for the web interface
        """
        self.page = page
        self.page.title = "Manufacturing Settings"
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        
        self._initialize_form_fields()
        self.setup_ui()
        self.setup_producer()
    
    def _initialize_form_fields(self):
        """Initialize all form input fields and controls."""
        # Required input fields
        self.machine_id_field = ft.TextField(
            label="Machine ID",
            hint_text="Enter machine identifier (e.g., MILL_001)",
            width=300
        )
        
        # Numeric input fields
        self.temperature_field = ft.TextField(
            label="Temperature (°C)",
            hint_text="Enter temperature setting",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.pressure_field = ft.TextField(
            label="Pressure (PSI)",
            hint_text="Enter pressure setting",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Dropdown selections
        self.machine_type_dropdown = ft.Dropdown(
            label="Machine Type",
            width=300,
            options=[
                ft.dropdown.Option("injection_molding"),
                ft.dropdown.Option("cnc_mill"),
                ft.dropdown.Option("assembly_line"),
                ft.dropdown.Option("packaging")
            ]
        )
        
        self.operation_mode_dropdown = ft.Dropdown(
            label="Operation Mode",
            width=300,
            options=[
                ft.dropdown.Option("production"),
                ft.dropdown.Option("maintenance"),
                ft.dropdown.Option("calibration"),
                ft.dropdown.Option("standby")
            ]
        )
        
        # Action button and status display
        self.submit_button = ft.ElevatedButton(
            text="Apply Settings",
            on_click=self.submit_data,
            width=300
        )
        
        self.status_text = ft.Text(
            "Ready to apply settings",
            color=ft.Colors.GREEN
        )
    
    def setup_producer(self):
        """Initialize Kafka producer connection using shared service.
        
        Connects to the output topic specified in environment variables.
        Updates UI status based on connection success/failure.
        """
        try:
            # Get output topic from environment variable or use default
            output_topic_name = os.environ.get("output", "data-input")
            
            # Initialize producer through shared service
            if shared_quix_service.initialize_producer(output_topic_name):
                self.status_text.value = f"Connected to topic: {output_topic_name}"
                self.status_text.color = ft.Colors.GREEN
            else:
                status = shared_quix_service.get_status()
                self.status_text.value = f"Error: {status['status']}"
                self.status_text.color = ft.Colors.RED
            
        except Exception as e:
            self.status_text.value = f"Error connecting producer: {str(e)}"
            self.status_text.color = ft.Colors.RED
            print(f"Error setting up producer: {e}")
        
        if self.page:
            self.page.update()
    
    def submit_data(self, e):
        """Handle form submission and validation.
        
        Validates all required fields, converts numeric values,
        creates message payload, and sends to Kafka topic.
        
        Args:
            e: Flet event object (unused but required by button callback)
        """
        try:
            # Validate all required fields are filled
            if not self._validate_required_fields():
                return
            
            # Parse and validate numeric fields
            try:
                temperature = float(self.temperature_field.value)
                pressure = float(self.pressure_field.value)
            except ValueError:
                self.show_error("Temperature and Pressure must be numeric values")
                return
            
            # Create structured message payload
            message_data = self._create_message_payload(temperature, pressure)
            
            # Send message through shared service
            if shared_quix_service.is_ready():
                shared_quix_service.send_message(message_data)
                self.show_success("Settings applied successfully!")
                self.clear_form()
            else:
                self.show_error("Producer not initialized")
                
        except Exception as ex:
            self.show_error(f"Error submitting data: {str(ex)}")
    
    def _validate_required_fields(self):
        """Validate that all required fields are filled.
        
        Returns:
            bool: True if all required fields are valid, False otherwise
        """
        if not self.machine_id_field.value:
            self.show_error("Machine ID is required")
            return False
            
        if not self.temperature_field.value:
            self.show_error("Temperature is required")
            return False
            
        if not self.pressure_field.value:
            self.show_error("Pressure is required")
            return False
        
        return True
    
    def _create_message_payload(self, temperature, pressure):
        """Create the structured message payload for Kafka.
        
        Args:
            temperature: Validated temperature value
            pressure: Validated pressure value
            
        Returns:
            dict: Structured message data ready for JSON serialization
        """
        return {
            "machine_id": self.machine_id_field.value,
            "temperature": temperature,
            "pressure": pressure,
            "machine_type": self.machine_type_dropdown.value or "unknown",
            "operation_mode": self.operation_mode_dropdown.value or "production",
            "timestamp": datetime.now().isoformat(),
            "source": "manufacturing-settings"
        }
    
    def show_success(self, message):
        """Display success message to user.
        
        Args:
            message: Success message to display
        """
        self.status_text.value = message
        self.status_text.color = ft.Colors.GREEN
        self.page.update()
        print(f"SUCCESS: {message}")
    
    def show_error(self, message):
        """Display error message to user.
        
        Args:
            message: Error message to display
        """
        self.status_text.value = message
        self.status_text.color = ft.Colors.RED
        self.page.update()
        print(f"ERROR: {message}")
    
    def clear_form(self):
        """Reset all form fields to empty/default values."""
        self.machine_id_field.value = ""
        self.temperature_field.value = ""
        self.pressure_field.value = ""
        self.machine_type_dropdown.value = None
        self.operation_mode_dropdown.value = None
        self.page.update()
    
    def setup_ui(self):
        """Create and layout the user interface components."""
        self.page.add(
            # Page title
            ft.Container(
                content=ft.Text(
                    "Manufacturing Machine Settings", 
                    style=ft.TextThemeStyle.HEADLINE_LARGE
                ),
                margin=ft.margin.only(bottom=30)
            ),
            
            # Main form container
            ft.Container(
                content=ft.Column([
                    ft.Text("Machine Settings", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.Container(height=20),  # Header spacer
                    
                    # Required fields section
                    self.machine_id_field,
                    ft.Container(height=10),
                    
                    self.temperature_field,
                    ft.Container(height=10),
                    
                    self.pressure_field,
                    ft.Container(height=20),  # Section spacer
                    
                    # Optional fields section
                    self.machine_type_dropdown,
                    ft.Container(height=10),
                    
                    self.operation_mode_dropdown,
                    ft.Container(height=30),  # Pre-button spacer
                    
                    # Action and status section
                    self.submit_button,
                    ft.Container(height=20),
                    
                    self.status_text
                ]),
                bgcolor=ft.Colors.GREY_900,
                padding=30,
                border_radius=10,
                width=400
            )
        )


def main(page: ft.Page):
    """Main application entry point.
    
    Args:
        page: Flet page object for the web interface
    """
    ManufacturingSettingsForm(page)


if __name__ == "__main__":
    # Start the Flet web application
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        port=80, 
        host="0.0.0.0"
    )