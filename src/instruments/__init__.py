"""Instrument drivers package."""

from instruments.psu import BK9130, BK9200
from instruments.eload import Chroma63600

# Map instrument types to driver classes
INSTRUMENT_DRIVERS = {
    "BK9130": BK9130,
    "BK9200": BK9200,
    "Chroma63600": Chroma63600,
}

__all__ = ["INSTRUMENT_DRIVERS", "BK9130", "BK9200", "Chroma63600"]

