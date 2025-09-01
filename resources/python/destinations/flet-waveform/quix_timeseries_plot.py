import flet as ft
import threading
import time
from datetime import datetime
from shared_quix_service import shared_quix_service


class QuixTimeseriesPlot:
    def __init__(self, title: str, y_axis_label: str, units: str, height: int = 300, 
                 update_callback=None, page_update_callback=None, update_interval: float = 1.0):
        """
        Create a custom timeseries plot component for Quix data with multiple series support
        
        Args:
            title: Title displayed above the chart
            y_axis_label: Label for the Y axis (e.g., "Temperature")
            units: Units for the data (e.g., "°C")
            height: Height of the chart in pixels
            update_callback: Function to call when data is updated (data_points, last_update_time)
            page_update_callback: Function to call to update the page
            update_interval: How often to update the chart in seconds
        """
        self.title = title
        self.y_axis_label = y_axis_label
        self.units = units
        self.height = height
        self.update_callback = update_callback
        self.page_update_callback = page_update_callback
        self.update_interval = update_interval
        
        # Dictionary to store series configurations (data is now in shared service)
        self.series_configs = {}
        
        # Thread control
        self.update_thread = None
        self.running = False
        
        # Create the chart component (initially empty)
        self.chart = ft.LineChart(
            data_series=[],  # Will be populated when series are added
            border=ft.border.all(1, ft.Colors.GREY_400),
            left_axis=ft.ChartAxis(
                title=ft.Text(f"{self.y_axis_label} ({self.units})", size=12),
                labels_size=40,
            ),
            bottom_axis=ft.ChartAxis(
                labels_size=0,  # Disabled built-in labels
            ),
            tooltip_bgcolor=ft.Colors.GREY_800,
            min_x=0.0,
            max_x=12.0,
            height=self.height,
            tooltip_max_content_width=500
        )
        
        # Custom time labels row
        self.time_labels_row = ft.Row(
            controls=[],
            alignment=ft.MainAxisAlignment.START,
            spacing=5
        )
        
        # Main container
        self.container = ft.Container(
            content=ft.Column([
                ft.Text(self.title, style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                self.chart,
                ft.Container(
                    content=self.time_labels_row,
                    margin=ft.margin.only(left=50)  # Align with chart axis
                ),
                ft.Container(
                    content=ft.Text("Time", size=12, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                    alignment=ft.alignment.center
                )
            ]),
            bgcolor=ft.Colors.GREY_900,
            padding=20,
            border_radius=10,
            margin=ft.margin.only(bottom=20)
        )
        
        # Start the update thread
        self.start_updates()
    
    def add_series(self, series_name: str, color: ft.Colors = ft.Colors.BLUE, stroke_width: int = 2):
        """
        Add a new data series to the plot
        
        Args:
            series_name: Name of the series
            color: Line color for this series
            stroke_width: Width of the line
        """
        if series_name not in self.series_configs:
            self.series_configs[series_name] = {
                'color': color,
                'stroke_width': stroke_width
            }
            
            # Add new data series to chart
            self.chart.data_series.append(
                ft.LineChartData(
                    stroke_width=stroke_width,
                    color=color,
                )
            )
    
    def add_data_point(self, series_name: str, timestamp, value):
        """
        Add a data point to a specific series
        
        Args:
            series_name: Name of the series to add data to
            timestamp: Timestamp in milliseconds
            value: Data value
        """
        if series_name not in self.series_configs:
            # Auto-create series with default settings
            self.add_series(series_name)
        
        # Store data in shared service using the provided timestamp and value
        shared_quix_service.add_data_point(series_name, timestamp, value)
        
        # Trigger callback
        if self.update_callback:
            try:
                total_points = self.get_data_point_count()
                current_time = datetime.now().strftime('%H:%M:%S')
                self.update_callback(total_points, current_time)
            except Exception as e:
                if "disconnected" in str(e).lower():
                    print(f"Plot callback disconnected, stopping updates...")
                    self.stop_updates()
                else:
                    print(f"Error in plot update callback: {e}")
    
    def update(self):
        """Update the chart with latest data from configured plot series"""
        if not self.series_configs:
            return
            
        all_chart_labels = []
        min_x = float('inf')
        max_x = float('-inf')
        
        # Update each configured series
        for i, series_name in enumerate(self.series_configs.keys()):
            chart_points, chart_labels = self._get_chart_data(series_name)
            
            if chart_points:
                self.chart.data_series[i].data_points = chart_points
                
                # Track min/max x values across all series
                series_min_x = chart_points[0].x
                series_max_x = chart_points[-1].x
                min_x = min(min_x, series_min_x)
                max_x = max(max_x, series_max_x)
                
                # Use labels from the first series (they should be similar across series)
                if i == 0:
                    all_chart_labels = chart_labels
        
        # Update chart bounds
        if min_x != float('inf'):
            self.chart.min_x = min_x
            self.chart.max_x = max_x
            
            # Update custom time labels
            self._update_time_labels(all_chart_labels)
    
    def _update_time_labels(self, chart_labels):
        """Update the custom time labels row below the chart"""
        # Clear existing labels
        self.time_labels_row.controls.clear()
        
        # Add new labels based on chart data with proper spacing
        for i, label in enumerate(chart_labels):
            timestamp = label.value
            time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%H:%M:%S")
            
            # Add container with flexible width to distribute labels evenly
            self.time_labels_row.controls.append(
                ft.Container(
                    content=ft.Text(
                        time_str,
                        size=12,  # Same size as vertical axis labels
                        color=ft.Colors.WHITE,  # Same color as vertical axis labels
                        text_align=ft.TextAlign.LEFT
                    ),
                    expand=True if i < len(chart_labels) - 1 else False
                )
            )
    
    def clear_data(self, series_name: str = None):
        """
        Clear data from the plot
        
        Args:
            series_name: Name of series to clear, or None to clear all series
        """
        # Clear data in shared service
        shared_quix_service.clear_data(series_name)
    
    def remove_series(self, series_name: str):
        """
        Remove a series completely from the plot
        
        Args:
            series_name: Name of series to remove
        """
        if series_name in self.series_configs:
            series_index = list(self.series_configs.keys()).index(series_name)
            del self.series_configs[series_name]
            shared_quix_service.clear_data(series_name)
            self.chart.data_series.pop(series_index)
    
    def get_series_names(self):
        """Get list of configured plot series names"""
        return list(self.series_configs.keys())
    
    def get_container(self):
        """Get the container widget to add to the page"""
        return self.container
    
    def set_y_range(self, min_y: float, max_y: float):
        """Set the Y-axis range"""
        self.chart.min_y = min_y
        self.chart.max_y = max_y
    
    def set_series_color(self, series_name: str, color: ft.Colors):
        """
        Change the line color for a specific series
        
        Args:
            series_name: Name of the series
            color: New color for the series
        """
        if series_name in self.series_configs:
            # Update config
            self.series_configs[series_name]['color'] = color
            
            # Update chart
            series_index = list(self.series_configs.keys()).index(series_name)
            self.chart.data_series[series_index].color = color
    
    def get_data_point_count(self, series_name: str = None):
        """
        Get the number of data points
        
        Args:
            series_name: Name of series, or None for total across all series
            
        Returns:
            Number of data points
        """
        if series_name is None:
            status = shared_quix_service.get_status()
            return status['total_points']
        else:
            data = shared_quix_service.get_series_data(series_name)
            return len(data)
    
    def start_updates(self):
        """Start the periodic chart update thread"""
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._periodic_update, daemon=True)
            self.update_thread.start()
    
    def stop_updates(self):
        """Stop the periodic chart update thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
    
    def _periodic_update(self):
        """Background thread for periodic chart updates"""
        while self.running:
            time.sleep(self.update_interval)
            try:
                self.update()
                # Trigger page update if callback provided
                if self.page_update_callback:
                    try:
                        self.page_update_callback()
                    except Exception as e:
                        print(f"Error in page update callback: {e}")
            except Exception as e:
                print(f"Error updating chart: {e}")
    
    def _get_chart_data(self, series_name):
        """Get data formatted for Flet LineChart for a specific series"""
        data_snapshot = shared_quix_service.get_series_data(series_name)
        if not data_snapshot:
            return [], []
        
        # Convert to chart points using timestamp as x-axis
        chart_points = []
        chart_x_labels = []
        
        for timestamp, value in data_snapshot:
            formatted_time = datetime.fromtimestamp(timestamp / 1000).strftime("%H:%M:%S")
            tooltip_text = f"Time: {formatted_time}\n{series_name}: {value:.1f} {self.units}"
            
            chart_points.append(ft.LineChartDataPoint(
                timestamp, 
                value,
                tooltip=tooltip_text
            ))
        
        # Create labels from data points
        if data_snapshot:
            max_labels = 4
            data_len = len(data_snapshot)
            step = max(1, data_len // max_labels) if data_len > max_labels else 1
            
            for i in range(0, data_len, step):
                timestamp = data_snapshot[i][0]
                chart_x_labels.append(ft.ChartAxisLabel(
                    timestamp,
                    ft.Text(
                        datetime.fromtimestamp(timestamp / 1000).strftime("%H:%M:%S"),
                        size=10,
                        bgcolor=ft.Colors.RED
                    )
                ))
        
        return chart_points, chart_x_labels