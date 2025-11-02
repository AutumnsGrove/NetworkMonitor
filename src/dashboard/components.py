"""
Reusable UI components for the Network Monitor dashboard.
"""
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc
import plotly.graph_objects as go
import requests
import logging
from typing import List, Dict, Any, Optional
from src.utils import format_bytes
from src.dashboard.styles import COLORS, CARD_STYLE, TABLE_STYLE

# Setup logging
logger = logging.getLogger(__name__)


def create_navbar():
    """
    Creates the navigation bar for the dashboard.

    Returns:
        dbc.NavbarSimple: Navigation bar component with links to all pages
    """
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Overview", href="/dashboard/")),
            dbc.NavItem(dbc.NavLink("Applications", href="/dashboard/applications")),
            dbc.NavItem(dbc.NavLink("Domains", href="/dashboard/domains")),
            dbc.NavItem(dbc.NavLink("History", href="/dashboard/history")),
            dbc.NavItem(dbc.NavLink("Config", href="/dashboard/config")),
        ],
        brand="Network Monitor",
        brand_href="/dashboard/",
        color="primary",
        dark=True,
        className="mb-4",
    )


def create_footer():
    """
    Creates the footer for the dashboard.

    Returns:
        html.Footer: Footer component with app information
    """
    from src.dashboard.styles import FOOTER_STYLE

    return html.Footer(
        html.Div([
            html.P([
                "Network Monitor Dashboard | ",
                "Privacy-First Network Usage Tracking | ",
                "All data stored locally"
            ]),
            html.P(
                "Powered by FastAPI + Dash",
                className="text-muted",
                style={"fontSize": "0.75rem"}
            ),
        ]),
        style=FOOTER_STYLE
    )


# ============================================================================
# API Communication Helper
# ============================================================================

def fetch_api_data(endpoint: str, timeout: int = 5) -> Dict:
    """
    Fetch data from API with improved error handling.

    Args:
        endpoint: API endpoint path (e.g., "/api/stats")
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Dict with API response or {"error": "message"} on failure
    """
    try:
        logger.debug(f"Fetching data from {endpoint}")
        response = requests.get(
            f"http://localhost:7500{endpoint}",
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"API timeout for {endpoint}")
        return {"error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        logger.error(f"API connection error for {endpoint}")
        return {"error": "Could not connect to API server"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"API HTTP error for {endpoint}: {e.response.status_code}")
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        logger.error(f"API unexpected error for {endpoint}: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


# ============================================================================
# Loading and Error Components
# ============================================================================

def create_loading_wrapper(component_id: str, component, loading_type: str = "default"):
    """
    Wraps any component with loading indicator.

    Args:
        component_id: ID for the loading wrapper
        component: Component to wrap with loading indicator
        loading_type: Type of loading spinner ("default", "circle", "dot", "cube")

    Returns:
        dcc.Loading component wrapping the provided component
    """
    return dcc.Loading(
        id=f"loading-{component_id}",
        type=loading_type,
        children=[component]
    )


def create_error_alert(message: str, title: str = "Error") -> dbc.Alert:
    """
    Creates an error alert component.

    Args:
        message: Error message to display
        title: Alert title (default: "Error")

    Returns:
        dbc.Alert component with error styling
    """
    return dbc.Alert(
        [
            html.H5(f"{title}", className="alert-heading"),
            html.P(message, className="mb-0"),
        ],
        color="danger",
        dismissable=True,
        className="mt-3"
    )


def create_empty_state(message: str, icon: str = None) -> html.Div:
    """
    Creates an empty state placeholder when no data is available.

    Args:
        message: Message to display
        icon: Optional emoji/icon to show (default: None)

    Returns:
        html.Div with centered empty state message
    """
    children = []

    if icon:
        children.append(
            html.Div(icon, className="empty-state-icon", style={"fontSize": "3rem", "marginBottom": "1rem"})
        )

    children.append(
        html.P(message, className="mb-0")
    )

    return html.Div(
        children,
        className="empty-state",
        style={
            "textAlign": "center",
            "padding": "3rem",
            "color": "#6c757d",
            "fontSize": "1.1rem"
        }
    )


def create_empty_figure_with_message(message: str) -> go.Figure:
    """
    Creates an empty Plotly figure with an error/info message.

    Args:
        message: Message to display in the empty figure

    Returns:
        Plotly figure with centered text annotation
    """
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="gray"),
        align="center"
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="white",
    )
    return fig


# ============================================================================
# Stat Card Components
# ============================================================================

def create_stat_card(title: str, value: str, icon: Optional[str] = None, color: str = "primary"):
    """
    Creates a statistics card component.

    Args:
        title: Card title/label
        value: Value to display
        icon: Optional icon class (not implemented yet)
        color: Bootstrap color (primary, success, info, warning, danger)

    Returns:
        dbc.Card: Card component with title and value
    """
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className="card-title text-muted mb-2"),
            html.H2(value, className=f"card-text text-{color} mb-0"),
        ]),
        style=CARD_STYLE,
        className="h-100",
    )


# ============================================================================
# Chart Components
# ============================================================================

def create_gauge_chart(value: float, max_value: float = 100, title: str = "Current Usage") -> go.Figure:
    """
    Creates a gauge chart for real-time bandwidth usage.

    Args:
        value: Current bandwidth value (MB/s)
        max_value: Maximum value for gauge scale (MB/s)
        title: Chart title

    Returns:
        Plotly figure with gauge indicator
    """
    # Color coding based on bandwidth thresholds
    if value < 1:
        gauge_color = COLORS["success"]  # Green < 1 MB/s
    elif value < 10:
        gauge_color = COLORS["warning"]  # Yellow 1-10 MB/s
    else:
        gauge_color = COLORS["danger"]   # Red > 10 MB/s

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 20}},
        number={"suffix": " MB/s", "font": {"size": 28}},
        gauge={
            "axis": {"range": [None, max_value], "ticksuffix": " MB/s"},
            "bar": {"color": gauge_color},
            "steps": [
                {"range": [0, 1], "color": "lightgray"},
                {"range": [1, 10], "color": "gray"},
                {"range": [10, max_value], "color": "darkgray"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": max_value * 0.9
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="white",
        font={"color": COLORS["dark"]},
    )

    return fig


def create_timeline_chart(data: List[Dict], title: str = "Network Usage Timeline") -> go.Figure:
    """
    Creates a timeline line chart for network usage over time.

    Args:
        data: List of {"timestamp": datetime, "bytes": int} dictionaries
        title: Chart title

    Returns:
        Plotly figure with line chart
    """
    if not data:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig

    # Extract timestamps and bytes
    timestamps = [d["timestamp"] for d in data]
    bytes_values = [d["bytes"] for d in data]

    # Create line chart
    fig = go.Figure(go.Scatter(
        x=timestamps,
        y=bytes_values,
        mode="lines+markers",
        name="Network Usage",
        line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Usage: %{customdata}<extra></extra>",
        customdata=[format_bytes(b) for b in bytes_values],
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Data Usage",
        height=400,
        margin=dict(l=60, r=40, t=60, b=60),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            tickformat=".2s",
        ),
    )

    return fig


def create_pie_chart(data: List[Dict], title: str = "Top Applications") -> go.Figure:
    """
    Creates a pie chart for top applications or domains.

    Args:
        data: List of {"name": str, "bytes": int} dictionaries
        title: Chart title

    Returns:
        Plotly figure with pie chart
    """
    if not data:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig

    # Extract names and bytes
    names = [d["name"] for d in data]
    bytes_values = [d["bytes"] for d in data]

    # Create pie chart
    fig = go.Figure(go.Pie(
        labels=names,
        values=bytes_values,
        hovertemplate="<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
        customdata=[format_bytes(b) for b in bytes_values],
        marker=dict(
            colors=[
                COLORS["primary"], COLORS["secondary"], COLORS["success"],
                COLORS["info"], COLORS["warning"], COLORS["danger"],
                "#6c757d", "#17a2b8", "#28a745", "#dc3545"
            ]
        ),
    ))

    fig.update_layout(
        title=title,
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor="white",
        font={"color": COLORS["dark"]},
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02
        ),
    )

    return fig


# ============================================================================
# Table Components (for Applications Page)
# ============================================================================

def create_applications_table(data: List[Dict]) -> dash_table.DataTable:
    """
    Creates a DataTable for displaying applications with sorting and pagination.

    Args:
        data: List of application dictionaries with keys:
              - id, process_name, bundle_id, bytes_sent, bytes_received,
                total_bytes, last_seen

    Returns:
        dash_table.DataTable configured for applications display
    """
    # Define columns with proper formatting
    columns = [
        {"name": "Application Name", "id": "process_name", "type": "text"},
        {"name": "Bundle ID", "id": "bundle_id", "type": "text"},
        {"name": "Bytes Sent", "id": "bytes_sent_formatted", "type": "text"},
        {"name": "Bytes Received", "id": "bytes_received_formatted", "type": "text"},
        {"name": "Total", "id": "total_bytes_formatted", "type": "text"},
        {"name": "Last Seen", "id": "last_seen", "type": "datetime"},
    ]

    # Create DataTable with styling
    return dash_table.DataTable(
        id="applications-table",
        columns=columns,
        data=data,
        sort_action="native",
        sort_mode="single",
        sort_by=[{"column_id": "total_bytes_formatted", "direction": "desc"}],
        page_action="native",
        page_current=0,
        page_size=25,
        row_selectable="single",
        selected_rows=[],
        **TABLE_STYLE
    )


def create_bar_chart(data: Dict, x_field: str, y_field: str, title: str) -> go.Figure:
    """
    Creates a generic bar chart for data comparison.

    Args:
        data: Dictionary with data for x and y axes
        x_field: Key for x-axis data
        y_field: Key for y-axis data
        title: Chart title

    Returns:
        Plotly figure with bar chart
    """
    if not data:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=350,
            margin=dict(l=60, r=40, t=60, b=60),
        )
        return fig

    # Create bar chart
    fig = go.Figure(go.Bar(
        x=data.get(x_field, []),
        y=data.get(y_field, []),
        marker_color=COLORS["primary"],
        hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title=x_field.replace("_", " ").title(),
        yaxis_title=y_field.replace("_", " ").title(),
        height=350,
        margin=dict(l=60, r=40, t=60, b=60),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
        ),
    )

    return fig


# ============================================================================
# Domain Components (for Domains Page)
# ============================================================================

def create_domain_tree(domains_data: List[Dict]) -> html.Div:
    """
    Creates a hierarchical tree structure for parent/child domains.

    Args:
        domains_data: List of domain dictionaries with parent relationships

    Returns:
        html.Div containing the domain tree structure
    """
    from src.dashboard.styles import TREE_STYLE, TREE_PARENT_STYLE, TREE_CHILD_STYLE

    if not domains_data:
        return html.Div(
            "No domains tracked yet",
            className="text-muted",
            style={"padding": "20px", "textAlign": "center"}
        )

    # Group domains by parent
    parent_domains = {}
    orphan_domains = []

    for domain in domains_data:
        domain_name = domain.get("domain", "Unknown")
        parent_domain = domain.get("parent_domain")
        total_bytes = domain.get("total_bytes", 0)
        browser = domain.get("browser", "Unknown")

        if not parent_domain or parent_domain == domain_name:
            # This is a parent domain
            if domain_name not in parent_domains:
                parent_domains[domain_name] = {
                    "data": domain,
                    "children": []
                }
        else:
            # This is a child domain
            if parent_domain not in parent_domains:
                parent_domains[parent_domain] = {
                    "data": {"domain": parent_domain, "total_bytes": 0, "browser": browser},
                    "children": []
                }
            parent_domains[parent_domain]["children"].append(domain)

    # Build tree HTML
    tree_items = []

    for parent_name, parent_info in sorted(parent_domains.items(), key=lambda x: x[1]["data"].get("total_bytes", 0), reverse=True):
        parent_data = parent_info["data"]
        children = parent_info["children"]

        # Calculate parent total (sum of children or parent's own bytes)
        if children:
            parent_total = sum(child.get("total_bytes", 0) for child in children)
        else:
            parent_total = parent_data.get("total_bytes", 0)

        # Parent domain item
        parent_item = html.Li([
            html.Span(
                f"• {parent_name} ({format_bytes(parent_total)})",
                style=TREE_PARENT_STYLE,
                **{"data-domain": parent_name}
            ),
            # Children list
            html.Ul([
                html.Li(
                    html.Span(
                        f"- {child.get('domain', 'Unknown')} ({format_bytes(child.get('total_bytes', 0))}) [{child.get('browser', 'N/A')}]",
                        style=TREE_CHILD_STYLE,
                        **{"data-domain": child.get('domain', 'Unknown')}
                    )
                )
                for child in sorted(children, key=lambda x: x.get("total_bytes", 0), reverse=True)
            ], style=TREE_STYLE) if children else html.Span()
        ], style={"listStyleType": "none", "marginBottom": "10px"})

        tree_items.append(parent_item)

    return html.Ul(tree_items, style=TREE_STYLE)


def create_domains_table(data: List[Dict]) -> dash_table.DataTable:
    """
    Creates a DataTable for displaying domains with sorting and pagination.

    Args:
        data: List of domain dictionaries with keys:
              - id, domain, parent_domain, browser, total_bytes, last_seen

    Returns:
        dash_table.DataTable configured for domains display
    """
    # Define columns with proper formatting
    columns = [
        {"name": "Domain", "id": "domain", "type": "text"},
        {"name": "Parent Domain", "id": "parent_domain", "type": "text"},
        {"name": "Browser", "id": "browser", "type": "text"},
        {"name": "Total Bytes", "id": "total_bytes_formatted", "type": "text"},
        {"name": "Last Seen", "id": "last_seen", "type": "datetime"},
    ]

    # Create DataTable with styling
    return dash_table.DataTable(
        id="domains-table",
        columns=columns,
        data=data,
        sort_action="native",
        sort_mode="single",
        sort_by=[{"column_id": "total_bytes_formatted", "direction": "desc"}],
        page_action="native",
        page_current=0,
        page_size=25,
        row_selectable="single",
        selected_rows=[],
        **TABLE_STYLE
    )


def create_area_chart(data: List[Dict], title: str = "Domain Usage Timeline") -> go.Figure:
    """
    Creates a stacked area chart for timeline data with multiple series.

    Args:
        data: List of dictionaries with timestamp and values for each browser
              [{"timestamp": "...", "Zen": 100, "Chrome": 50, "Safari": 25}, ...]
        title: Chart title

    Returns:
        Plotly figure with stacked area chart
    """
    if not data:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=60, r=40, t=60, b=40),
        )
        return fig

    # Extract timestamps
    timestamps = [d.get("timestamp", "") for d in data]

    # Determine which browsers have data
    browsers = []
    for d in data:
        for key in d.keys():
            if key != "timestamp" and key not in browsers:
                browsers.append(key)

    # Color mapping for browsers
    browser_colors = {
        "Zen": COLORS["primary"],
        "Chrome": COLORS["success"],
        "Safari": COLORS["info"],
        "Firefox": COLORS["warning"],
        "Other": COLORS["secondary"],
    }

    # Create figure with stacked area traces
    fig = go.Figure()

    for browser in browsers:
        values = [d.get(browser, 0) for d in data]

        fig.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            mode="lines",
            name=browser,
            line=dict(color=browser_colors.get(browser, COLORS["primary"]), width=0),
            fill='tonexty' if browsers.index(browser) > 0 else 'tozeroy',
            hovertemplate=f"<b>{browser}</b><br>%{{x}}<br>%{{customdata}}<extra></extra>",
            customdata=[format_bytes(v) for v in values],
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Data Usage",
        height=400,
        margin=dict(l=60, r=40, t=60, b=60),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            tickformat=".2s",
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )

    return fig


# ============================================================================
# Historical Analysis Components
# ============================================================================

def create_heatmap(data: List[List[float]], title: str = "Hourly Usage Heatmap") -> go.Figure:
    """
    Creates a heatmap for hourly usage patterns (day × hour).

    Args:
        data: 7×24 matrix (list of lists) where rows=days (0=Mon, 6=Sun), cols=hours (0-23)
              Values represent total bytes for that hour
        title: Chart title

    Returns:
        Plotly figure with heatmap
    """
    if not data or len(data) != 7:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=60, r=40, t=60, b=60),
        )
        return fig

    # Create heatmap
    fig = go.Figure(go.Heatmap(
        z=data,
        x=[f"{h}:00" for h in range(24)],  # Hour labels
        y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        colorscale="Blues",
        hovertemplate="<b>%{y} at %{x}</b><br>Usage: %{customdata}<extra></extra>",
        customdata=[[format_bytes(val) for val in row] for row in data],
        colorbar=dict(
            title="Data Usage",
            tickformat=".2s",
        )
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        height=400,
        margin=dict(l=80, r=40, t=60, b=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(
            side="bottom",
            tickmode="linear",
            tick0=0,
            dtick=2,  # Show every 2 hours
        ),
    )

    return fig


def create_multi_line_chart(datasets: List[Dict], title: str, x_label: str = "Day", y_label: str = "Data Usage") -> go.Figure:
    """
    Creates a multi-line chart for comparing multiple time series.

    Args:
        datasets: List of {"name": str, "x_values": list, "y_values": list}
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label

    Returns:
        Plotly figure with multiple lines
    """
    if not datasets:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=60, r=40, t=60, b=60),
        )
        return fig

    # Color and line style mapping
    colors_palette = [COLORS["primary"], COLORS["success"], COLORS["secondary"]]
    line_styles = ["solid", "dash", "dot"]

    fig = go.Figure()

    # Add each dataset as a line
    for idx, dataset in enumerate(datasets):
        name = dataset.get("name", f"Series {idx+1}")
        x_values = dataset.get("x_values", [])
        y_values = dataset.get("y_values", [])

        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines+markers",
            name=name,
            line=dict(
                color=colors_palette[idx % len(colors_palette)],
                width=2,
                dash=line_styles[idx % len(line_styles)]
            ),
            marker=dict(size=6),
            hovertemplate=f"<b>{name}</b><br>%{{x}}<br>%{{customdata}}<extra></extra>",
            customdata=[format_bytes(b) for b in y_values],
        ))

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=400,
        margin=dict(l=60, r=40, t=60, b=60),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            tickformat=".2s",
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )

    return fig


def create_monthly_bar_chart(months_data: List[Dict], title: str = "Monthly Comparison") -> go.Figure:
    """
    Creates a bar chart for monthly usage comparison.

    Args:
        months_data: List of {"month": str, "total_bytes": int, "is_current": bool}
        title: Chart title

    Returns:
        Plotly figure with bar chart
    """
    if not months_data:
        # Empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=60, r=40, t=60, b=60),
        )
        return fig

    # Extract data
    months = [d.get("month", "Unknown") for d in months_data]
    bytes_values = [d.get("total_bytes", 0) for d in months_data]
    is_current = [d.get("is_current", False) for d in months_data]

    # Color coding: current month highlighted
    colors = [COLORS["primary"] if current else COLORS["secondary"] for current in is_current]

    fig = go.Figure(go.Bar(
        x=months,
        y=bytes_values,
        marker_color=colors,
        text=[format_bytes(b) for b in bytes_values],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title="Total Data Usage",
        height=400,
        margin=dict(l=60, r=40, t=80, b=60),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            tickformat=".2s",
        ),
    )

    return fig


# ============================================================================
# Date Utility Functions
# ============================================================================

def get_week_dates(offset: int = 0):
    """
    Get start and end dates for a week.

    Args:
        offset: Week offset (0=current week, -1=last week, etc.)

    Returns:
        Tuple of (start_date, end_date) as datetime.date objects
    """
    from datetime import datetime, timedelta

    today = datetime.now().date()
    # Find Monday of current week
    days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
    current_monday = today - timedelta(days=days_since_monday)

    # Apply offset
    start_date = current_monday + timedelta(weeks=offset)
    end_date = start_date + timedelta(days=6)  # Sunday

    return start_date, end_date


def get_month_dates(offset: int = 0):
    """
    Get start and end dates for a month.

    Args:
        offset: Month offset (0=current month, -1=last month, etc.)

    Returns:
        Tuple of (start_date, end_date) as datetime.date objects
    """
    from datetime import datetime
    from calendar import monthrange

    today = datetime.now().date()

    # Calculate target month and year
    target_month = today.month + offset
    target_year = today.year

    # Handle year rollovers
    while target_month < 1:
        target_month += 12
        target_year -= 1
    while target_month > 12:
        target_month -= 12
        target_year += 1

    # Get first day of month
    start_date = datetime(target_year, target_month, 1).date()

    # Get last day of month
    days_in_month = monthrange(target_year, target_month)[1]
    end_date = datetime(target_year, target_month, days_in_month).date()

    return start_date, end_date


def format_date_for_api(date) -> str:
    """
    Convert datetime to ISO format string for API calls.

    Args:
        date: datetime.date or datetime.datetime object

    Returns:
        ISO format string "YYYY-MM-DD"
    """
    from datetime import datetime, date as date_type

    if isinstance(date, str):
        return date

    if isinstance(date, datetime):
        return date.strftime("%Y-%m-%d")

    if isinstance(date, date_type):
        return date.strftime("%Y-%m-%d")

    return str(date)


# ============================================================================
# Configuration Page Components
# ============================================================================

def create_system_status_card(status_data: Dict) -> dbc.Card:
    """
    Creates a system status card showing daemon and database information.

    Args:
        status_data: Dictionary with daemon status, DB info, etc.

    Returns:
        dbc.Card with formatted system information
    """
    # Extract daemon status
    daemon_running = status_data.get("daemon_running", False)
    daemon_uptime = status_data.get("daemon_uptime", "N/A")
    sampling_interval = status_data.get("sampling_interval", 5)

    # Extract database info
    db_path = status_data.get("db_path", "N/A")
    db_size = status_data.get("db_size", 0)
    sample_count = status_data.get("sample_count", 0)

    # Extract aggregation info
    last_aggregation = status_data.get("last_aggregation", "Never")

    # Create status badge
    if daemon_running:
        status_badge = dbc.Badge("Running", color="success", className="me-2")
    else:
        status_badge = dbc.Badge("Stopped", color="danger", className="me-2")

    return dbc.Card([
        dbc.CardHeader("System Health", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5(["Daemon Status: ", status_badge], className="mb-3"),
                ], width=12, md=4),

                dbc.Col([
                    html.H5(f"Uptime: {daemon_uptime}", className="mb-3"),
                ], width=12, md=4),

                dbc.Col([
                    html.H5(f"Sampling: {sampling_interval}s", className="mb-3"),
                ], width=12, md=4),
            ]),

            dbc.Row([
                dbc.Col([
                    html.P([
                        html.Strong("Database Path: "),
                        html.Code(db_path, style={"fontSize": "0.85rem"})
                    ], className="mb-2"),
                ], width=12),
            ]),

            dbc.Row([
                dbc.Col([
                    html.P([
                        html.Strong("Database Size: "),
                        html.Span(format_bytes(db_size))
                    ], className="mb-2"),
                ], width=12, md=4),

                dbc.Col([
                    html.P([
                        html.Strong("Sample Count: "),
                        html.Span(f"{sample_count:,}")
                    ], className="mb-2"),
                ], width=12, md=4),

                dbc.Col([
                    html.P([
                        html.Strong("Last Aggregation: "),
                        html.Span(last_aggregation)
                    ], className="mb-2"),
                ], width=12, md=4),
            ]),
        ])
    ], style=CARD_STYLE)


def format_uptime(start_timestamp: Optional[str]) -> str:
    """
    Format uptime from start timestamp.

    Args:
        start_timestamp: Start timestamp (Unix timestamp or ISO string)

    Returns:
        Formatted uptime string (e.g., "2 days, 5 hours, 23 minutes")
    """
    from datetime import datetime

    if not start_timestamp:
        return "N/A"

    try:
        # Try parsing as Unix timestamp first
        if isinstance(start_timestamp, (int, float)):
            start_time = datetime.fromtimestamp(start_timestamp)
        else:
            # Try parsing as ISO string
            start_time = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))

        # Calculate uptime
        uptime_seconds = (datetime.now() - start_time).total_seconds()

        # Format using existing utility
        from src.utils import format_duration
        return format_duration(int(uptime_seconds))

    except Exception as e:
        return "N/A"


def get_database_size(db_path: Optional[str] = None) -> int:
    """
    Get size of SQLite database file.

    Args:
        db_path: Path to database file (optional, uses default if not provided)

    Returns:
        Size in bytes
    """
    import os
    from src.utils import get_db_path

    if not db_path:
        db_path = str(get_db_path())

    try:
        if os.path.exists(db_path):
            return os.path.getsize(db_path)
    except Exception:
        pass

    return 0
