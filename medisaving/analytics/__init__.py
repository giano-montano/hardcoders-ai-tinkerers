"""Owned by analytics team. No HTTP or presentation dependencies."""
from . import basket as basket_module
from . import rank as rank_module
from .basket import basket
from .rank import rank


def register(areas):
    parser = areas.add_parser("analytics", help="Calculate compact results locally")
    commands = parser.add_subparsers(required=True)
    rank_module.register(commands)
    basket_module.register(commands)
