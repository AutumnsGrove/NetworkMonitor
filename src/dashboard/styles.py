"""
CSS styling constants for the Network Monitor dashboard.
Provides consistent color scheme and styling across all dashboard components.
"""

# Color Scheme - Network Theme (Blues and Greens)
COLORS = {
    "primary": "#0066cc",      # Primary blue
    "secondary": "#00994d",    # Network green
    "success": "#28a745",      # Success green
    "info": "#17a2b8",         # Info cyan
    "warning": "#ffc107",      # Warning yellow
    "danger": "#dc3545",       # Danger red
    "light": "#f8f9fa",        # Light background
    "dark": "#343a40",         # Dark text
    "muted": "#6c757d",        # Muted text
    "background": "#ffffff",   # Main background
    "card_bg": "#f8f9fa",      # Card background
    "border": "#dee2e6",       # Border color
}

# Navbar Styles
NAVBAR_STYLE = {
    "padding": "1rem 2rem",
    "marginBottom": "2rem",
    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
}

# Card Styles
CARD_STYLE = {
    "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
    "borderRadius": "8px",
    "marginBottom": "1.5rem",
}

CARD_HEADER_STYLE = {
    "backgroundColor": COLORS["primary"],
    "color": "white",
    "fontWeight": "bold",
    "padding": "0.75rem 1.25rem",
}

CARD_BODY_STYLE = {
    "padding": "1.25rem",
}

# Container Styles
CONTAINER_STYLE = {
    "padding": "2rem 1rem",
    "maxWidth": "1400px",
}

# Common Spacing
SPACING = {
    "small": "0.5rem",
    "medium": "1rem",
    "large": "1.5rem",
    "xlarge": "2rem",
}

# Graph Styles
GRAPH_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "pan2d",
        "lasso2d",
        "select2d",
        "autoScale2d",
    ],
}

# Footer Styles
FOOTER_STYLE = {
    "textAlign": "center",
    "padding": "1rem",
    "marginTop": "2rem",
    "borderTop": f"1px solid {COLORS['border']}",
    "color": COLORS["muted"],
    "fontSize": "0.875rem",
}

# DataTable Styles
TABLE_STYLE = {
    "style_table": {"overflowX": "auto"},
    "style_cell": {
        "textAlign": "left",
        "padding": "10px",
        "fontFamily": "Arial, sans-serif",
    },
    "style_header": {
        "backgroundColor": COLORS["primary"],
        "color": "white",
        "fontWeight": "bold",
    },
    "style_data_conditional": [
        {
            "if": {"row_index": "odd"},
            "backgroundColor": "rgb(248, 248, 248)",
        }
    ],
}

# Domain Tree Styles
TREE_STYLE = {
    "listStyleType": "none",
    "paddingLeft": "20px",
    "fontFamily": "Arial, sans-serif",
}

TREE_PARENT_STYLE = {
    "fontWeight": "bold",
    "color": COLORS["primary"],
    "cursor": "pointer",
    "fontSize": "1rem",
    "marginBottom": "5px",
    "display": "inline-block",
}

TREE_CHILD_STYLE = {
    "color": COLORS["dark"],
    "cursor": "pointer",
    "paddingLeft": "15px",
    "fontSize": "0.9rem",
    "display": "inline-block",
}

# ============================================================================
# Responsive Design Styles
# ============================================================================

# Breakpoint constants
MOBILE_BREAKPOINT = "768px"
TABLET_BREAKPOINT = "1024px"

# Responsive container style
RESPONSIVE_CONTAINER_STYLE = {
    **CONTAINER_STYLE,
    "padding": "0.5rem",  # Less padding on mobile
}

# Responsive card style
RESPONSIVE_CARD_STYLE = {
    **CARD_STYLE,
    "marginBottom": "1rem",  # Tighter spacing on mobile
}

# Responsive graph style
RESPONSIVE_GRAPH_STYLE = {
    "height": "400px",  # Default desktop height
}

# Table responsive wrapper
TABLE_RESPONSIVE_STYLE = {
    "overflowX": "auto",
    "-webkit-overflow-scrolling": "touch",  # Smooth scrolling on iOS
}
