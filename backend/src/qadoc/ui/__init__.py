"""
UI Presentation Layer for QADoc (Streamlit adapter).
"""

from qadoc.ui.auth import render_auth_screen
from qadoc.ui.sidebar import render_sidebar
from qadoc.ui.uploader import render_document_uploader
from qadoc.ui.components import render_sources_badges

__all__ = [
    "render_auth_screen",
    "render_sidebar",
    "render_document_uploader",
    "render_sources_badges",
]
