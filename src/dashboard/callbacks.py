"""
Dash callbacks for interactivity and data updates.
Handles all user interactions and real-time data updates for the dashboard.
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html
from datetime import datetime
import plotly.graph_objs as go
import requests

# Import app instance for callback registration
from src.dashboard.app_instance import app

from src.dashboard.components import (
    fetch_api_data,
    create_stat_card,
    create_gauge_chart,
    create_timeline_chart,
    create_pie_chart,
    create_applications_table,
    create_bar_chart,
    create_domain_tree,
    create_domains_table,
    create_area_chart,
    create_heatmap,
    create_multi_line_chart,
    create_monthly_bar_chart,
    get_week_dates,
    get_month_dates,
    format_date_for_api,
)
from src.utils import format_bytes
from src.dashboard.styles import COLORS


# ============================================================================
# Overview Page Callbacks
# ============================================================================

@app.callback(
    Output("stats-cards", "children"),
    Input("overview-interval", "n_intervals")
)
def update_stats_cards(n):
    """
    Update quick statistics cards with latest data.

    Args:
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        List of stat card components
    """
    # Fetch stats from API
    stats = fetch_api_data("/api/stats")

    # Default values if API fails
    if not stats:
        stats = {
            "today": {"total_bytes": 0, "top_app": None, "top_domain": None},
            "this_week": {"total_bytes": 0},
            "this_month": {"total_bytes": 0},
            "current": {"active_connections": 0}
        }

    # Extract values with proper nesting
    today = stats.get("today", {})
    week = stats.get("this_week", {})
    month = stats.get("this_month", {})
    current = stats.get("current", {})

    # Get top app name (API returns string or None, not dict)
    top_app = today.get("top_app")
    top_app_name = top_app if top_app else "N/A"

    # Get top domain name (API returns string or None, not dict)
    top_domain = today.get("top_domain")
    top_domain_name = top_domain if top_domain else "N/A"

    # Get active connections count
    active_count = current.get("active_connections", 0)

    # Create stat cards
    cards = [
        dbc.Col([
            create_stat_card(
                "Total Data Today",
                format_bytes(today.get("total_bytes", 0)),
                color="primary"
            )
        ], width=12, md=6, lg=4, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Total Data This Week",
                format_bytes(week.get("total_bytes", 0)),
                color="info"
            )
        ], width=12, md=6, lg=4, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Total Data This Month",
                format_bytes(month.get("total_bytes", 0)),
                color="success"
            )
        ], width=12, md=6, lg=4, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Top Application Today",
                top_app_name,
                color="primary"
            )
        ], width=12, md=6, lg=4, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Top Domain Today",
                top_domain_name,
                color="info"
            )
        ], width=12, md=6, lg=4, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Active Connections",
                str(active_count),
                color="success"
            )
        ], width=12, md=6, lg=4, className="mb-3"),
    ]

    return dbc.Row(cards)


@app.callback(
    Output("overview-gauge", "figure"),
    Input("overview-interval", "n_intervals")
)
def update_gauge(n):
    """
    Update real-time bandwidth gauge.

    Args:
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        Plotly gauge figure
    """
    # For now, calculate bandwidth from recent samples
    # In a real implementation, this would be calculated from the last 5 seconds of data
    stats = fetch_api_data("/api/stats")

    # Mock current bandwidth (you could enhance this with a dedicated endpoint)
    # For now, estimate from recent activity
    current_bandwidth_mbps = 0.0

    if stats and stats.get("total_today", 0) > 0:
        # Simple mock: assume some percentage of daily usage is current
        # This is a placeholder - real implementation would use recent samples
        current_bandwidth_mbps = 0.5  # Placeholder value

    return create_gauge_chart(
        value=current_bandwidth_mbps,
        max_value=50,  # 50 MB/s max scale
        title="Current Bandwidth Usage"
    )


@app.callback(
    Output("overview-timeline", "figure"),
    Input("time-range-selector", "value"),
    Input("overview-interval", "n_intervals")
)
def update_timeline(period, n):
    """
    Update timeline chart based on selected time range.

    Args:
        period: Selected time period (1h, 24h, 7d, 30d, 90d)
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        Plotly timeline figure
    """
    # Fetch timeline data from API
    api_response = fetch_api_data(f"/api/stats/timeline?period={period}")

    # Extract timeline array from response
    if not api_response or "timeline" not in api_response:
        timeline_data = []
    else:
        timeline_data = api_response["timeline"]

    # Transform API data to expected format for chart
    chart_data = []
    for item in timeline_data:
        chart_data.append({
            "timestamp": item.get("timestamp", datetime.now().isoformat()),
            "bytes": item.get("total_bytes", 0)  # API returns total_bytes
        })

    # Create title with period label
    period_labels = {
        "1h": "Last Hour",
        "24h": "Last 24 Hours",
        "7d": "Last 7 Days",
        "30d": "Last 30 Days",
        "90d": "Last 90 Days",
    }
    title = f"Network Usage Timeline - {period_labels.get(period, period)}"

    return create_timeline_chart(chart_data, title=title)


@app.callback(
    Output("apps-pie-chart", "figure"),
    Input("overview-interval", "n_intervals")
)
def update_apps_pie(n):
    """
    Update top applications pie chart.

    Args:
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        Plotly pie chart figure
    """
    # Fetch top applications
    api_response = fetch_api_data("/api/applications?limit=10")

    # Extract applications array from response
    if not api_response or "applications" not in api_response:
        apps_data = []
    else:
        apps_data = api_response["applications"]

    # Transform API data to expected format
    chart_data = []
    for app in apps_data:
        chart_data.append({
            "name": app.get("process_name", "Unknown"),
            "bytes": app.get("total_bytes", 0)
        })

    return create_pie_chart(chart_data, title="Top 10 Applications")


@app.callback(
    Output("domains-pie-chart", "figure"),
    Input("overview-interval", "n_intervals")
)
def update_domains_pie(n):
    """
    Update top domains pie chart.

    Args:
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        Plotly pie chart figure
    """
    # Fetch top domains
    api_response = fetch_api_data("/api/domains/top/10?period=today")

    # Extract top_domains array from response
    if not api_response or "top_domains" not in api_response:
        domains_data = []
    else:
        domains_data = api_response["top_domains"]

    # Transform API data to expected format
    chart_data = []
    for domain in domains_data:
        chart_data.append({
            "name": domain.get("domain", "Unknown"),
            "bytes": domain.get("total_bytes", 0)
        })

    return create_pie_chart(chart_data, title="Top 10 Domains (Today)")


# ============================================================================
# Applications Page Callbacks
# ============================================================================

@app.callback(
    Output("applications-table-container", "children"),
    Output("app-compare-checklist", "options"),
    Input("app-search-input", "value")
)
def update_applications_table(search_term):
    """
    Load all applications, optionally filtered by search term.

    Args:
        search_term: Search string for filtering by name or bundle ID

    Returns:
        Tuple of (table component, checklist options for comparison)
    """
    # Fetch all applications from API
    api_response = fetch_api_data("/api/applications")

    if not api_response or "applications" not in api_response:
        return html.Div("No applications found", className="text-muted"), []

    apps_data = api_response["applications"]

    # Filter by search term if provided
    if search_term:
        search_lower = search_term.lower()
        apps_data = [
            app for app in apps_data
            if search_lower in app.get("process_name", "").lower()
            or search_lower in app.get("bundle_id", "").lower()
        ]

    # Format data for table display
    table_data = []
    for app in apps_data:
        table_data.append({
            "id": app.get("id"),
            "process_name": app.get("process_name", "Unknown"),
            "bundle_id": app.get("bundle_id", "N/A"),
            "bytes_sent": app.get("bytes_sent", 0),
            "bytes_received": app.get("bytes_received", 0),
            "total_bytes": app.get("total_bytes", 0),
            "bytes_sent_formatted": format_bytes(app.get("bytes_sent", 0)),
            "bytes_received_formatted": format_bytes(app.get("bytes_received", 0)),
            "total_bytes_formatted": format_bytes(app.get("total_bytes", 0)),
            "last_seen": app.get("last_seen", "N/A"),
        })

    # Create checklist options for comparison
    checklist_options = [
        {"label": f"{app.get('process_name', 'Unknown')} ({format_bytes(app.get('total_bytes', 0))})",
         "value": app.get("id")}
        for app in apps_data[:10]  # Limit to top 10 for comparison
    ]

    # Create table
    table = create_applications_table(table_data)

    return table, checklist_options


@app.callback(
    Output("selected-app-details", "style"),
    Output("selected-app-title", "children"),
    Input("applications-table", "selected_rows"),
    State("applications-table", "data")
)
def show_app_details(selected_rows, table_data):
    """
    Display details for selected application.

    Args:
        selected_rows: List of selected row indices
        table_data: Current table data

    Returns:
        Tuple of (visibility style, app title)
    """
    if not selected_rows or not table_data:
        return {"display": "none"}, ""

    # Get selected app data
    selected_app = table_data[selected_rows[0]]
    app_name = selected_app.get("process_name", "Unknown")

    # Show the details section
    return {"display": "block"}, f"Details: {app_name}"


@app.callback(
    Output("app-timeline", "figure"),
    Input("applications-table", "selected_rows"),
    State("applications-table", "data")
)
def update_app_timeline(selected_rows, table_data):
    """
    Update timeline for selected application.

    Args:
        selected_rows: List of selected row indices
        table_data: Current table data

    Returns:
        Plotly timeline figure
    """
    if not selected_rows or not table_data:
        return go.Figure()

    # Get app_id from selected row
    selected_app = table_data[selected_rows[0]]
    app_id = selected_app.get("id")
    app_name = selected_app.get("process_name", "Unknown")

    if not app_id:
        return go.Figure()

    # Fetch timeline data from API
    api_response = fetch_api_data(f"/api/applications/{app_id}/timeline")

    if not api_response or "timeline" not in api_response:
        timeline_data = []
    else:
        timeline_data = api_response["timeline"]

    # Transform to chart format
    chart_data = []
    for item in timeline_data:
        chart_data.append({
            "timestamp": item.get("timestamp", datetime.now().isoformat()),
            "bytes": item.get("total_bytes", 0)
        })

    return create_timeline_chart(chart_data, title=f"Timeline: {app_name}")


@app.callback(
    Output("app-breakdown", "figure"),
    Output("app-packets", "figure"),
    Input("applications-table", "selected_rows"),
    State("applications-table", "data")
)
def update_app_breakdown(selected_rows, table_data):
    """
    Update breakdown charts for selected application.

    Args:
        selected_rows: List of selected row indices
        table_data: Current table data

    Returns:
        Tuple of (bytes breakdown figure, packets breakdown figure)
    """
    if not selected_rows or not table_data:
        return go.Figure(), go.Figure()

    # Get selected app data
    selected_app = table_data[selected_rows[0]]

    # Create bytes breakdown (Sent vs Received)
    bytes_data = {
        "category": ["Sent", "Received"],
        "bytes": [selected_app.get("bytes_sent", 0), selected_app.get("bytes_received", 0)]
    }

    bytes_fig = go.Figure(go.Bar(
        x=bytes_data["category"],
        y=bytes_data["bytes"],
        marker_color=[COLORS["danger"], COLORS["success"]],
        text=[format_bytes(b) for b in bytes_data["bytes"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>",
    ))

    bytes_fig.update_layout(
        title="Sent vs Received (Bytes)",
        xaxis_title="Direction",
        yaxis_title="Bytes",
        height=350,
        margin=dict(l=60, r=40, t=60, b=60),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        yaxis=dict(showgrid=True, gridcolor="lightgray"),
    )

    # Create packets breakdown (mock data - real implementation would fetch from API)
    # For now, estimate packets based on bytes (assume ~1500 bytes per packet)
    packets_sent = selected_app.get("bytes_sent", 0) // 1500
    packets_received = selected_app.get("bytes_received", 0) // 1500

    packets_data = {
        "category": ["Sent", "Received"],
        "packets": [packets_sent, packets_received]
    }

    packets_fig = go.Figure(go.Bar(
        x=packets_data["category"],
        y=packets_data["packets"],
        marker_color=[COLORS["danger"], COLORS["success"]],
        text=[f"{p:,}" for p in packets_data["packets"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{text} packets<extra></extra>",
    ))

    packets_fig.update_layout(
        title="Sent vs Received (Packets)",
        xaxis_title="Direction",
        yaxis_title="Packet Count",
        height=350,
        margin=dict(l=60, r=40, t=60, b=60),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        yaxis=dict(showgrid=True, gridcolor="lightgray"),
    )

    return bytes_fig, packets_fig


@app.callback(
    Output("app-comparison-timeline", "figure"),
    Input("app-compare-checklist", "value")
)
def update_comparison_timeline(selected_app_ids):
    """
    Compare multiple applications on one timeline.

    Args:
        selected_app_ids: List of app IDs to compare

    Returns:
        Plotly timeline figure with multiple lines
    """
    if not selected_app_ids:
        # Return empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="Select applications to compare",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            title="Application Comparison",
            height=400,
            margin=dict(l=60, r=40, t=60, b=60),
        )
        return fig

    # Color palette for different apps
    colors_palette = [
        COLORS["primary"], COLORS["secondary"], COLORS["success"],
        COLORS["info"], COLORS["warning"], COLORS["danger"]
    ]

    fig = go.Figure()

    # Fetch timeline for each selected app
    for idx, app_id in enumerate(selected_app_ids):
        api_response = fetch_api_data(f"/api/applications/{app_id}/timeline")

        if not api_response or "timeline" not in api_response:
            continue

        timeline_data = api_response["timeline"]

        # Extract timestamps and bytes
        timestamps = [item.get("timestamp", datetime.now().isoformat()) for item in timeline_data]
        bytes_values = [item.get("total_bytes", 0) for item in timeline_data]

        # Get app name from first data point (or fetch separately)
        app_name = api_response.get("process_name", f"App {app_id}")

        # Add line to chart
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=bytes_values,
            mode="lines+markers",
            name=app_name,
            line=dict(color=colors_palette[idx % len(colors_palette)], width=2),
            marker=dict(size=4),
            hovertemplate=f"<b>{app_name}</b><br>%{{x}}<br>%{{customdata}}<extra></extra>",
            customdata=[format_bytes(b) for b in bytes_values],
        ))

    fig.update_layout(
        title="Application Comparison Timeline",
        xaxis_title="Time",
        yaxis_title="Data Usage",
        height=400,
        margin=dict(l=60, r=40, t=60, b=60),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": COLORS["dark"]},
        xaxis=dict(showgrid=True, gridcolor="lightgray"),
        yaxis=dict(showgrid=True, gridcolor="lightgray", tickformat=".2s"),
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
# Domains Page Callbacks
# ============================================================================

@app.callback(
    Output("domains-table-container", "children"),
    Input("browser-filter", "value"),
    Input("parent-only-switch", "value")
)
def update_domains_table(browser, parent_only):
    """
    Load domains table filtered by browser and parent-only setting.

    Args:
        browser: Selected browser filter (All, Zen, Chrome, Safari)
        parent_only: Boolean indicating if only parent domains should be shown

    Returns:
        DataTable component with filtered domains
    """
    # Build query params
    params = []
    if parent_only:
        params.append("parent_only=true")
    if browser and browser != "All":
        params.append(f"browser={browser}")

    # Construct query string
    query_string = "?" + "&".join(params) if params else ""

    # Call API
    api_response = fetch_api_data(f"/api/domains{query_string}")

    if not api_response or "domains" not in api_response:
        return html.Div("No domains found", className="text-muted")

    domains_data = api_response["domains"]

    # Format data for table display
    table_data = []
    for domain in domains_data:
        # NOTE: Browser field may not be available in current API
        # Using domain_id as id since API returns domain_id
        table_data.append({
            "id": domain.get("domain_id", domain.get("id")),
            "domain": domain.get("domain", "Unknown"),
            "parent_domain": domain.get("parent_domain", "N/A"),
            "browser": domain.get("browser", "Mixed"),  # TODO: API doesn't return browser yet
            "total_bytes": domain.get("total_bytes", 0),
            "total_bytes_formatted": format_bytes(domain.get("total_bytes", 0)),
            "last_seen": domain.get("last_seen", "N/A"),
        })

    # Create table
    return create_domains_table(table_data)


@app.callback(
    Output("domain-tree", "children"),
    Input("browser-filter", "value"),
    Input("parent-only-switch", "value")
)
def update_domain_tree(browser, parent_only):
    """
    Update domain hierarchy tree based on filters.

    Args:
        browser: Selected browser filter
        parent_only: Boolean indicating if only parent domains should be shown

    Returns:
        html.Div containing domain tree structure
    """
    # Build query params (same as table)
    params = []
    if parent_only:
        params.append("parent_only=true")
    if browser and browser != "All":
        params.append(f"browser={browser}")

    # Construct query string
    query_string = "?" + "&".join(params) if params else ""

    # Fetch domains
    api_response = fetch_api_data(f"/api/domains{query_string}")

    if not api_response or "domains" not in api_response:
        return html.Div("No domains tracked yet", className="text-muted")

    domains_data = api_response["domains"]

    # Create tree structure
    return create_domain_tree(domains_data)


@app.callback(
    Output("selected-domain-details", "style"),
    Output("selected-domain-title", "children"),
    Input("domains-table", "selected_rows"),
    State("domains-table", "data")
)
def show_domain_details(selected_rows, table_data):
    """
    Display details for selected domain.

    Args:
        selected_rows: List of selected row indices
        table_data: Current table data

    Returns:
        Tuple of (visibility style, domain title)
    """
    if not selected_rows or not table_data:
        return {"display": "none"}, ""

    # Get selected domain data
    selected_domain = table_data[selected_rows[0]]
    domain_name = selected_domain.get("domain", "Unknown")

    # Show the details section
    return {"display": "block"}, f"Details: {domain_name}"


@app.callback(
    Output("domain-timeline", "figure"),
    Input("domains-table", "selected_rows"),
    State("domains-table", "data")
)
def update_domain_timeline(selected_rows, table_data):
    """
    Show timeline for selected domain.

    Args:
        selected_rows: List of selected row indices
        table_data: Current table data

    Returns:
        Plotly timeline figure
    """
    if not selected_rows or not table_data:
        return go.Figure()

    # Get domain from selected row
    selected_domain = table_data[selected_rows[0]]
    domain_name = selected_domain.get("domain", "Unknown")

    # NOTE: Domain timeline endpoint may not exist yet
    # For now, use mock data or /api/stats/timeline as fallback
    # TODO: Implement GET /api/domains/{domain_id}/timeline endpoint

    # Try to fetch timeline (this may fail if endpoint doesn't exist)
    domain_id = selected_domain.get("id")
    if domain_id:
        api_response = fetch_api_data(f"/api/domains/{domain_id}/timeline")

        if api_response and "timeline" in api_response:
            timeline_data = api_response["timeline"]

            # Transform to chart format
            chart_data = []
            for item in timeline_data:
                chart_data.append({
                    "timestamp": item.get("timestamp", datetime.now().isoformat()),
                    "bytes": item.get("total_bytes", 0)
                })

            return create_timeline_chart(chart_data, title=f"Timeline: {domain_name}")

    # Fallback: Return empty chart with message
    fig = go.Figure()
    fig.add_annotation(
        text="Timeline data not available (endpoint not implemented)",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        title=f"Timeline: {domain_name}",
        height=400,
        margin=dict(l=60, r=40, t=60, b=60),
    )
    return fig


@app.callback(
    Output("domain-browser-breakdown", "figure"),
    Input("domains-table", "selected_rows"),
    State("domains-table", "data")
)
def update_browser_breakdown(selected_rows, table_data):
    """
    Show browser distribution for selected domain.

    Args:
        selected_rows: List of selected row indices
        table_data: Current table data

    Returns:
        Plotly pie chart figure
    """
    if not selected_rows or not table_data:
        return go.Figure()

    # Get domain details
    selected_domain = table_data[selected_rows[0]]
    domain_name = selected_domain.get("domain", "Unknown")

    # NOTE: Browser breakdown endpoint may not exist
    # For now, use mock data based on current browser if available
    # TODO: Implement per-browser stats for domains

    # Create mock breakdown (placeholder data)
    # In reality, this would query all records for this domain grouped by browser
    browser = selected_domain.get("browser", "Unknown")
    total_bytes = selected_domain.get("total_bytes", 0)

    # Mock distribution (in real implementation, query API for browser breakdown)
    chart_data = [
        {"name": browser, "bytes": total_bytes}
    ]

    # If we want to show a more realistic mock:
    # Assume some distribution across browsers
    if browser != "N/A" and browser != "Unknown":
        chart_data = [
            {"name": browser, "bytes": int(total_bytes * 0.7)},
            {"name": "Other", "bytes": int(total_bytes * 0.3)},
        ]

    return create_pie_chart(chart_data, title=f"Browser Distribution: {domain_name}")


# ============================================================================
# History Page Callbacks
# ============================================================================

@app.callback(
    Output("history-date-range", "start_date"),
    Output("history-date-range", "end_date"),
    Input("preset-this-week", "n_clicks"),
    Input("preset-last-week", "n_clicks"),
    Input("preset-this-month", "n_clicks"),
    Input("preset-last-month", "n_clicks"),
    Input("preset-90-days", "n_clicks"),
    prevent_initial_call=True
)
def update_date_range_from_preset(tw, lw, tm, lm, nd):
    """
    Update date range based on preset button clicks.

    Args:
        tw: This week button clicks
        lw: Last week button clicks
        tm: This month button clicks
        lm: Last month button clicks
        nd: 90 days button clicks

    Returns:
        Tuple of (start_date, end_date)
    """
    from dash import ctx
    from datetime import timedelta

    # Determine which button was clicked
    if not ctx.triggered:
        # No button clicked, shouldn't happen with prevent_initial_call
        return None, None

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "preset-this-week":
        start_date, end_date = get_week_dates(offset=0)
    elif button_id == "preset-last-week":
        start_date, end_date = get_week_dates(offset=-1)
    elif button_id == "preset-this-month":
        start_date, end_date = get_month_dates(offset=0)
    elif button_id == "preset-last-month":
        start_date, end_date = get_month_dates(offset=-1)
    elif button_id == "preset-90-days":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
    else:
        # Fallback
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

    return start_date, end_date


@app.callback(
    Output("hourly-heatmap", "figure"),
    Input("history-date-range", "start_date"),
    Input("history-date-range", "end_date")
)
def update_hourly_heatmap(start_date, end_date):
    """
    Generate hourly heatmap for selected date range.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        Plotly heatmap figure
    """
    # Fetch real data from API
    api_response = fetch_api_data(f"/api/historical/heatmap?start_date={start_date}&end_date={end_date}")

    if not api_response or "data" not in api_response:
        # No data available
        return create_heatmap(
            [],
            title=f"Hourly Usage Heatmap ({start_date} to {end_date})"
        )

    # Transform API response to expected format for heatmap
    heatmap_data = api_response["data"]

    return create_heatmap(
        heatmap_data,
        title=f"Hourly Usage Heatmap ({start_date} to {end_date})"
    )


@app.callback(
    Output("weekly-trends", "figure"),
    Input("history-date-range", "start_date"),
    Input("history-date-range", "end_date")
)
def update_weekly_trends(start_date, end_date):
    """
    Compare current week vs last week vs average.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        Plotly multi-line figure
    """
    # Fetch real weekly comparison data from API
    api_response = fetch_api_data("/api/historical/weekly")

    if not api_response or "data" not in api_response:
        # No data available
        return create_multi_line_chart(
            [],
            title="Weekly Trends Comparison",
            x_label="Day of Week",
            y_label="Data Usage"
        )

    # Transform API response to datasets format
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    datasets = [
        {
            "name": "Current Week",
            "data": [day["current_week"] for day in api_response["data"]],
            "x": day_names
        },
        {
            "name": "Last Week",
            "data": [day["last_week"] for day in api_response["data"]],
            "x": day_names
        },
        {
            "name": "Average",
            "data": [day["average"] for day in api_response["data"]],
            "x": day_names
        }
    ]

    return create_multi_line_chart(
        datasets,
        title="Weekly Trends Comparison",
        x_label="Day of Week",
        y_label="Data Usage"
    )


@app.callback(
    Output("monthly-comparison", "figure"),
    Input("history-date-range", "start_date"),
    Input("history-date-range", "end_date")
)
def update_monthly_comparison(start_date, end_date):
    """
    Show monthly comparison bar chart.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        Plotly bar chart figure
    """
    # Fetch real monthly data from API
    api_response = fetch_api_data("/api/historical/monthly?months=6")

    if not api_response or "data" not in api_response:
        # No data available
        return create_monthly_bar_chart(
            [],
            title="Monthly Data Usage Comparison"
        )

    # Transform API response to expected format
    months_data = api_response["data"]

    return create_monthly_bar_chart(
        months_data,
        title="Monthly Data Usage Comparison"
    )


@app.callback(
    Output("history-summary-cards", "children"),
    Input("history-date-range", "start_date"),
    Input("history-date-range", "end_date")
)
def update_summary_cards(start_date, end_date):
    """
    Show summary statistics for selected period.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        List of stat card components
    """
    from datetime import datetime, timedelta

    # Parse dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    except:
        # Fallback to last 30 days
        end = datetime.now().date()
        start = end - timedelta(days=30)

    # Calculate period duration
    period_days = (end - start).days + 1

    # Real implementation would query database:
    # SELECT
    #   SUM(total_bytes) as total,
    #   AVG(total_bytes) as avg_daily,
    #   MAX(total_bytes) as peak,
    #   MIN(total_bytes) as lowest
    # FROM daily_aggregates
    # WHERE date BETWEEN start_date AND end_date

    # TODO: Replace with actual API call
    # api_response = fetch_api_data(f"/api/stats/summary?start_date={start_date}&end_date={end_date}")

    # Generate mock summary stats
    import random
    total_bytes = random.uniform(50_000_000_000, 200_000_000_000) * (period_days / 30)
    avg_daily = total_bytes / period_days
    peak_bytes = avg_daily * random.uniform(1.5, 2.5)
    lowest_bytes = avg_daily * random.uniform(0.3, 0.6)

    # Create stat cards
    cards = [
        dbc.Col([
            create_stat_card(
                "Total Data in Period",
                format_bytes(total_bytes),
                color="primary"
            )
        ], width=12, md=6, lg=3, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Average Daily Usage",
                format_bytes(avg_daily),
                color="info"
            )
        ], width=12, md=6, lg=3, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Peak Usage Day",
                format_bytes(peak_bytes),
                color="success"
            )
        ], width=12, md=6, lg=3, className="mb-3"),

        dbc.Col([
            create_stat_card(
                "Lowest Usage Day",
                format_bytes(lowest_bytes),
                color="secondary"
            )
        ], width=12, md=6, lg=3, className="mb-3"),
    ]

    return dbc.Row(cards)


# ============================================================================
# Config Page Callbacks
# ============================================================================

@app.callback(
    Output("system-status-card", "children"),
    Input("config-interval", "n_intervals")
)
def update_system_status(n):
    """
    Fetch and display current system status.

    Args:
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        System status card component
    """
    from src.dashboard.components import create_system_status_card, format_uptime, get_database_size
    from src.utils import get_db_path

    # Fetch daemon status
    daemon_status = fetch_api_data("/api/config/daemon/status")

    # Fetch summary stats for sample count
    summary_stats = fetch_api_data("/api/stats/summary")

    # Get database info
    db_path = str(get_db_path())
    db_size = get_database_size(db_path)

    # Get last aggregation time
    config_data = fetch_api_data("/api/config")
    last_aggregation = "Never"
    if config_data and "config" in config_data:
        last_agg_raw = config_data["config"].get("last_aggregation")
        if last_agg_raw:
            last_aggregation = last_agg_raw

    # Get actual sampling interval from config
    config_all = fetch_api_data("/api/config/all")
    sampling_interval = 1  # default
    if config_all and "config" in config_all:
        if "daemon.sampling_interval_seconds" in config_all["config"]:
            sampling_interval = int(config_all["config"]["daemon.sampling_interval_seconds"]["value"])

    # Build status data
    status_data = {
        "daemon_running": daemon_status.get("running", False) if daemon_status else False,
        "daemon_uptime": format_uptime(daemon_status.get("start_time")) if daemon_status else "N/A",
        "sampling_interval": sampling_interval,
        "db_path": db_path,
        "db_size": db_size,
        "sample_count": summary_stats.get("total_samples", 0) if summary_stats else 0,
        "last_aggregation": last_aggregation,
    }

    return create_system_status_card(status_data)


@app.callback(
    Output("sampling-interval-slider", "value"),
    Output("retention-raw-slider", "value"),
    Output("retention-hourly-slider", "value"),
    Output("web-server-port-input", "value"),
    Output("log-level-dropdown", "value"),
    Input("config-interval", "n_intervals")
)
def load_current_config(n):
    """
    Load current configuration from API.

    Args:
        n: Number of intervals elapsed (triggers refresh)

    Returns:
        Tuple of 5 values for each form field
    """
    # Fetch config from new endpoint
    api_response = fetch_api_data("/api/config/all")

    # Default values
    sampling = 1
    retention_raw = 7
    retention_hourly = 90
    port = 7500
    log_level = "INFO"

    if api_response and "config" in api_response:
        config = api_response["config"]

        # Extract values from new format (config keys have "section.key" format)
        # Each value is a dict with "value" and "source" keys
        if "daemon.sampling_interval_seconds" in config:
            sampling = int(config["daemon.sampling_interval_seconds"]["value"])

        if "retention.raw_samples_days" in config:
            retention_raw = int(config["retention.raw_samples_days"]["value"])

        if "retention.hourly_aggregates_days" in config:
            retention_hourly = int(config["retention.hourly_aggregates_days"]["value"])

        if "server.port" in config:
            port = int(config["server.port"]["value"])

        if "logging.level" in config:
            log_level = config["logging.level"]["value"]

    return sampling, retention_raw, retention_hourly, port, log_level


@app.callback(
    Output("settings-save-status", "children"),
    Input("save-settings-button", "n_clicks"),
    State("sampling-interval-slider", "value"),
    State("retention-raw-slider", "value"),
    State("retention-hourly-slider", "value"),
    State("web-server-port-input", "value"),
    State("log-level-dropdown", "value"),
    prevent_initial_call=True
)
def save_settings(n_clicks, sampling, retention_raw, retention_hourly, port, log_level):
    """
    Save configuration changes via API.

    Args:
        n_clicks: Number of button clicks
        sampling: Sampling interval value
        retention_raw: Raw data retention days
        retention_hourly: Hourly aggregates retention days
        port: Web server port
        log_level: Log level string

    Returns:
        Success/error alert
    """
    if not n_clicks:
        return ""

    # Build config updates
    updates = {
        "sampling_interval_seconds": str(sampling),
        "data_retention_days_raw": str(retention_raw),
        "data_retention_days_hourly": str(retention_hourly),
        "web_server_port": str(port),
        "log_level": str(log_level),
    }

    # Track success/failure
    errors = []

    # Update each config value via API
    for key, value in updates.items():
        try:
            response = requests.put(
                "http://localhost:7500/api/config",
                json={"key": key, "value": value},
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            errors.append(f"{key}: {str(e)}")

    # Return result
    if errors:
        return dbc.Alert(
            [
                html.H5("Save Failed", className="alert-heading"),
                html.P("The following errors occurred:"),
                html.Ul([html.Li(err) for err in errors])
            ],
            color="danger",
            dismissable=True
        )
    else:
        restart_needed = False
        if "web_server_port" in updates:
            restart_needed = True

        message = "Settings saved successfully!"
        if restart_needed:
            message += " Note: Restart required for port changes to take effect."

        return dbc.Alert(
            message,
            color="success",
            dismissable=True
        )


@app.callback(
    Output("operations-status", "children", allow_duplicate=True),
    Input("force-aggregation-button", "n_clicks"),
    prevent_initial_call=True
)
def force_aggregation(n_clicks):
    """
    Manually trigger data aggregation.

    Args:
        n_clicks: Number of button clicks

    Returns:
        Status alert
    """
    if not n_clicks:
        return ""

    try:
        response = requests.post(
            "http://localhost:7500/api/config/aggregate",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return dbc.Alert(
            [
                html.H5("✓ Aggregation Complete", className="alert-heading"),
                html.P(f"Successfully aggregated data:"),
                html.Ul([
                    html.Li(f"Hourly aggregates: {data.get('hourly_aggregates', 0)}"),
                    html.Li(f"Daily aggregates: {data.get('daily_aggregates', 0)}")
                ])
            ],
            color="success",
            dismissable=True
        )
    except Exception as e:
        return dbc.Alert(
            [
                html.H5("Aggregation Failed", className="alert-heading"),
                html.P(f"Error: {str(e)}")
            ],
            color="danger",
            dismissable=True
        )


@app.callback(
    Output("operations-status", "children", allow_duplicate=True),
    Input("clear-samples-button", "n_clicks"),
    prevent_initial_call=True
)
def clear_old_samples(n_clicks):
    """
    Manually clear samples beyond retention period.

    Args:
        n_clicks: Number of button clicks

    Returns:
        Status alert
    """
    if not n_clicks:
        return ""

    try:
        response = requests.post(
            "http://localhost:7500/api/config/cleanup",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return dbc.Alert(
            [
                html.H5("✓ Cleanup Complete", className="alert-heading"),
                html.P(f"Successfully cleaned up old data:"),
                html.Ul([
                    html.Li(f"Raw samples deleted: {data.get('deleted_samples', 0)}"),
                    html.Li(f"Hourly aggregates deleted: {data.get('deleted_hourly', 0)}")
                ])
            ],
            color="success",
            dismissable=True
        )
    except Exception as e:
        return dbc.Alert(
            [
                html.H5("Cleanup Failed", className="alert-heading"),
                html.P(f"Error: {str(e)}")
            ],
            color="danger",
            dismissable=True
        )


@app.callback(
    Output("operations-status", "children", allow_duplicate=True),
    Input("refresh-cache-button", "n_clicks"),
    prevent_initial_call=True
)
def refresh_cache(n_clicks):
    """
    Clear internal caches.

    Args:
        n_clicks: Number of button clicks

    Returns:
        Status alert
    """
    if not n_clicks:
        return ""

    try:
        response = requests.post(
            "http://localhost:7500/api/config/refresh-cache",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        return dbc.Alert(
            [
                html.H5("✓ Cache Cleared", className="alert-heading"),
                html.P("Successfully cleared all internal caches:"),
                html.Ul([html.Li(cache) for cache in data.get('caches_cleared', [])])
            ],
            color="success",
            dismissable=True
        )
    except Exception as e:
        return dbc.Alert(
            [
                html.H5("Cache Refresh Failed", className="alert-heading"),
                html.P(f"Error: {str(e)}")
            ],
            color="danger",
            dismissable=True
        )


@app.callback(
    Output("operations-status", "children", allow_duplicate=True),
    Input("export-data-button", "n_clicks"),
    prevent_initial_call=True
)
def export_data(n_clicks):
    """
    Trigger data export.

    Args:
        n_clicks: Number of button clicks

    Returns:
        Alert with download instructions
    """
    if not n_clicks:
        return ""

    try:
        # Get export data from API
        response = requests.get(
            "http://localhost:7500/api/export?format=csv",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return dbc.Alert(
            [
                html.H5("✓ Export Ready", className="alert-heading"),
                html.P(f"Exported {data.get('rows', 0)} rows of data"),
                html.P([
                    html.Strong("Download: "),
                    html.A(
                        "Click here to download CSV",
                        href="http://localhost:7500/api/export?format=csv",
                        target="_blank",
                        className="alert-link"
                    )
                ]),
                html.P([
                    html.Small("Note: Data is limited to 10,000 most recent hourly aggregates")
                ], className="mb-0")
            ],
            color="success",
            dismissable=True
        )
    except Exception as e:
        return dbc.Alert(
            [
                html.H5("Export Failed", className="alert-heading"),
                html.P(f"Error: {str(e)}"),
                html.P([
                    html.Strong("Alternative: "),
                    "Database file is located at ~/.netmonitor/network_monitor.db"
                ], className="mb-0 small")
            ],
            color="danger",
            dismissable=True
        )
