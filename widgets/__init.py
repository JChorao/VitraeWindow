"""Módulo de widgets do dashboard"""

from .clock import ClockWidget
from .weather import WeatherWidget
from .spotify import SpotifyWidget
from .calendar_widget import CalendarWidget 
from .emergency import EmergencyButton

__all__ = [
    'ClockWidget',
    'WeatherWidget',
    'SpotifyWidget',
    'CalendarWidget',
    'EmergencyButton'
]