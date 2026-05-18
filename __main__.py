"""
Entry point for module execution: python -m weekly_planner
"""

try:
    from .main import main
except ImportError:
    from main import main

if __name__ == "__main__":
    main()
