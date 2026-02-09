"""Batch processor for P1812 radio propagation calculations.

NOTE: This module has been updated to use batch_processor_v2 which includes
smart filename generation and spreadsheet export functionality.
See batch_processor_v2.py for the latest implementation.
"""

# Import from v2 for backward compatibility
from .batch_processor_v2 import main, batch_process


if __name__ == "__main__":
    main()
