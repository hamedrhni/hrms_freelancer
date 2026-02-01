# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
HRMS Freelancer setup module
"""

from hrms_freelancer.setup.install import after_install, before_uninstall

__all__ = ["after_install", "before_uninstall"]
