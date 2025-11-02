"""
Page layouts for the Network Monitor dashboard.
Each function returns a layout for a specific dashboard page.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from src.dashboard.styles import CONTAINER_STYLE, CARD_STYLE


def overview_layout():
    """
    Layout for the Overview dashboard page.

    Returns:
        dbc.Container: Overview page layout with real-time data and charts
    """
    return dbc.Container([
        # Page Title
        html.H1("Overview Dashboard", className="mb-4"),
        html.Hr(),

        # Auto-refresh interval component (30 seconds)
        dcc.Interval(
            id="overview-interval",
            interval=30000,  # 30 seconds in milliseconds
            n_intervals=0
        ),

        # Row 1: Real-time Bandwidth Gauge
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="loading-overview-gauge",
                    type="circle",
                    children=[dcc.Graph(id="overview-gauge")]
                )
            ], width=12, lg=12, className="mb-4")
        ]),

        # Row 2: Timeline with Time Range Selector
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label("Time Range:", className="fw-bold me-3"),
                    dcc.RadioItems(
                        id="time-range-selector",
                        options=[
                            {"label": " 1 Hour", "value": "1h"},
                            {"label": " 24 Hours", "value": "24h"},
                            {"label": " 7 Days", "value": "7d"},
                            {"label": " 30 Days", "value": "30d"},
                            {"label": " 90 Days", "value": "90d"},
                        ],
                        value="24h",
                        inline=True,
                        className="mb-3"
                    ),
                ]),
                dcc.Loading(
                    id="loading-overview-timeline",
                    type="default",
                    children=[dcc.Graph(id="overview-timeline")]
                )
            ], width=12, className="mb-4")
        ]),

        # Row 3: Pie Charts (Top Apps and Top Domains)
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="loading-apps-pie",
                    type="default",
                    children=[dcc.Graph(id="apps-pie-chart")]
                )
            ], width=12, lg=6, className="mb-4"),
            dbc.Col([
                dcc.Loading(
                    id="loading-domains-pie",
                    type="default",
                    children=[dcc.Graph(id="domains-pie-chart")]
                )
            ], width=12, lg=6, className="mb-4"),
        ]),

        # Row 4: Quick Stats Cards (6 cards in 2 rows)
        html.H3("Quick Statistics", className="mb-3"),
        html.Div(id="stats-cards"),

    ], style=CONTAINER_STYLE)


def applications_layout():
    """
    Layout for the Applications page with sortable table and detailed analytics.

    Returns:
        dbc.Container: Applications page layout with table and charts
    """
    return dbc.Container([
        # Page Title
        html.H1("Application Details", className="mb-4"),
        html.Hr(),

        # Search Bar Section
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    id="app-search-input",
                    type="text",
                    placeholder="Search by name or bundle ID...",
                    className="mb-3"
                )
            ], width=12, md=6)
        ]),

        # Applications Table Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("All Applications", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-applications-table",
                            type="default",
                            children=[html.Div(id="applications-table-container")]
                        )
                    ])
                ], style=CARD_STYLE)
            ], width=12, className="mb-4")
        ]),

        # Selected Application Details Section (initially hidden)
        html.Div(
            id="selected-app-details",
            style={"display": "none"},
            children=[
                html.Hr(),
                html.H3(id="selected-app-title", className="mb-3"),

                # App Timeline
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Network Usage Timeline", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                            dbc.CardBody([
                                dcc.Loading(
                                    id="loading-app-timeline",
                                    type="default",
                                    children=[dcc.Graph(id="app-timeline")]
                                )
                            ])
                        ], style=CARD_STYLE)
                    ], width=12, className="mb-4")
                ]),

                # Data Breakdown Charts
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Sent vs Received (Bytes)", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                            dbc.CardBody([
                                dcc.Graph(id="app-breakdown")
                            ])
                        ], style=CARD_STYLE)
                    ], width=12, md=6, className="mb-4"),

                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Sent vs Received (Packets)", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                            dbc.CardBody([
                                dcc.Graph(id="app-packets")
                            ])
                        ], style=CARD_STYLE)
                    ], width=12, md=6, className="mb-4"),
                ]),
            ]
        ),

        # Multi-App Comparison Section
        html.Hr(),
        html.H3("Compare Applications", className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Select applications to compare:", className="fw-bold mb-2"),
                dcc.Checklist(
                    id="app-compare-checklist",
                    options=[],  # Will be populated by callback
                    value=[],
                    inline=False,
                    className="mb-3"
                )
            ], width=12, md=4, className="mb-3"),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Comparison Timeline", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Graph(id="app-comparison-timeline")
                    ])
                ], style=CARD_STYLE)
            ], width=12, md=8, className="mb-4"),
        ]),

    ], style=CONTAINER_STYLE)


def domains_layout():
    """
    Layout for the Domains Analysis page with hierarchy visualization.

    Returns:
        dbc.Container: Domains page layout with filters, tree, and analytics
    """
    return dbc.Container([
        # Page Title
        html.H1("Domain Analysis", className="mb-4"),
        html.Hr(),

        # Top Section: Filters
        dbc.Row([
            dbc.Col([
                html.Label("Browser Filter:", className="fw-bold mb-2"),
                dbc.RadioItems(
                    id="browser-filter",
                    options=[
                        {"label": " All Browsers", "value": "All"},
                        {"label": " Zen", "value": "Zen"},
                        {"label": " Chrome", "value": "Chrome"},
                        {"label": " Safari", "value": "Safari"},
                    ],
                    value="All",
                    inline=True,
                    className="mb-3"
                )
            ], width=12, md=8),

            dbc.Col([
                dbc.Switch(
                    id="parent-only-switch",
                    label="Show parent domains only",
                    value=False,
                    className="mb-3"
                )
            ], width=12, md=4, className="text-md-end"),
        ], className="mb-4"),

        # Middle Section: Tree and Table
        dbc.Row([
            # Left Column: Domain Tree
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Domain Hierarchy", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-domain-tree",
                            type="default",
                            children=[html.Div(id="domain-tree", style={"maxHeight": "500px", "overflowY": "auto"})]
                        )
                    ])
                ], style=CARD_STYLE)
            ], width=12, lg=5, className="mb-4"),

            # Right Column: Domains Table
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("All Domains", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-domains-table",
                            type="default",
                            children=[html.Div(id="domains-table-container")]
                        )
                    ])
                ], style=CARD_STYLE)
            ], width=12, lg=7, className="mb-4"),
        ]),

        # Bottom Section: Selected Domain Analytics
        html.Div(
            id="selected-domain-details",
            style={"display": "none"},
            children=[
                html.Hr(),
                html.H3(id="selected-domain-title", className="mb-3"),

                # Domain Timeline
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Domain Usage Timeline", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                            dbc.CardBody([
                                dcc.Graph(id="domain-timeline")
                            ])
                        ], style=CARD_STYLE)
                    ], width=12, lg=8, className="mb-4"),

                    # Browser Breakdown
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Browser Distribution", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                            dbc.CardBody([
                                dcc.Graph(id="domain-browser-breakdown")
                            ])
                        ], style=CARD_STYLE)
                    ], width=12, lg=4, className="mb-4"),
                ]),
            ]
        ),

    ], style=CONTAINER_STYLE)


def history_layout():
    """
    Layout for the Historical Analysis page with advanced analytics.

    Returns:
        dbc.Container: History page layout with heatmaps and trend analysis
    """
    from datetime import datetime, timedelta

    # Calculate default date range (last 30 days)
    end_date = datetime.now().date()
    start_date = (end_date - timedelta(days=30))

    return dbc.Container([
        # Page Title
        html.H1("Historical Analysis", className="mb-4"),
        html.Hr(),

        # Date Range Picker Section
        dbc.Row([
            dbc.Col([
                html.Label("Select Date Range:", className="fw-bold mb-2"),
                dcc.DatePickerRange(
                    id="history-date-range",
                    start_date=start_date,
                    end_date=end_date,
                    display_format="MMM DD, YYYY",
                    className="mb-3"
                )
            ], width=12, md=6, className="mb-3"),

            dbc.Col([
                html.Label("Quick Presets:", className="fw-bold mb-2"),
                dbc.ButtonGroup([
                    dbc.Button("This Week", id="preset-this-week", size="sm", outline=True, color="primary"),
                    dbc.Button("Last Week", id="preset-last-week", size="sm", outline=True, color="primary"),
                    dbc.Button("This Month", id="preset-this-month", size="sm", outline=True, color="primary"),
                    dbc.Button("Last Month", id="preset-last-month", size="sm", outline=True, color="primary"),
                    dbc.Button("Last 90 Days", id="preset-90-days", size="sm", outline=True, color="primary"),
                ], className="d-flex flex-wrap gap-2")
            ], width=12, md=6, className="mb-3"),
        ], className="mb-4"),

        # Section 1: Hourly Heatmap
        html.H3("Hourly Usage Patterns", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Hourly Heatmap (Day × Hour)", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-hourly-heatmap",
                            type="default",
                            children=[dcc.Graph(id="hourly-heatmap")]
                        )
                    ])
                ], style=CARD_STYLE)
            ], width=12, className="mb-4")
        ]),

        # Section 2: Weekly Trends Comparison
        html.H3("Weekly Trends", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Current vs Previous Weeks", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Graph(id="weekly-trends")
                    ])
                ], style=CARD_STYLE)
            ], width=12, className="mb-4")
        ]),

        # Section 3: Monthly Comparison
        html.H3("Monthly Overview", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Monthly Comparison", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dcc.Graph(id="monthly-comparison")
                    ])
                ], style=CARD_STYLE)
            ], width=12, className="mb-4")
        ]),

        # Section 4: Summary Statistics
        html.H3("Period Summary", className="mb-3"),
        html.Div(id="history-summary-cards"),

    ], style=CONTAINER_STYLE)


def config_layout():
    """
    Layout for the Configuration page with system status, settings, and manual operations.

    Returns:
        dbc.Container: Config page layout with controls and status
    """
    return dbc.Container([
        # Page Title
        html.H1("Configuration & System Control", className="mb-4"),
        html.Hr(),

        # Auto-refresh interval component (10 seconds)
        dcc.Interval(
            id="config-interval",
            interval=10000,  # 10 seconds
            n_intervals=0
        ),

        # Section 1: System Status
        html.H3("System Status", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="loading-system-status",
                    type="circle",
                    children=[html.Div(id="system-status-card")]
                )
            ], width=12, className="mb-4")
        ]),

        # Section 2: Settings Form
        html.Hr(),
        html.H3("Configuration Settings", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("System Configuration", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        # Sampling Interval
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Sampling Interval (seconds)", className="fw-bold"),
                                html.Div([
                                    dcc.Slider(
                                        id="sampling-interval-slider",
                                        min=1,
                                        max=60,
                                        step=1,
                                        value=5,
                                        marks={1: "1s", 10: "10s", 20: "20s", 30: "30s", 40: "40s", 60: "60s"},
                                        tooltip={"placement": "bottom", "always_visible": True}
                                    ),
                                ], className="mb-3"),
                            ], width=12)
                        ]),

                        # Data Retention - Raw Samples
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Data Retention - Raw Samples (days)", className="fw-bold"),
                                html.Div([
                                    dcc.Slider(
                                        id="retention-raw-slider",
                                        min=1,
                                        max=30,
                                        step=1,
                                        value=7,
                                        marks={1: "1", 7: "7", 14: "14", 21: "21", 30: "30"},
                                        tooltip={"placement": "bottom", "always_visible": True}
                                    ),
                                ], className="mb-3"),
                            ], width=12)
                        ]),

                        # Data Retention - Hourly Aggregates
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Data Retention - Hourly Aggregates (days)", className="fw-bold"),
                                html.Div([
                                    dcc.Slider(
                                        id="retention-hourly-slider",
                                        min=1,
                                        max=365,
                                        step=1,
                                        value=90,
                                        marks={1: "1", 30: "30", 90: "90", 180: "180", 365: "365"},
                                        tooltip={"placement": "bottom", "always_visible": True}
                                    ),
                                ], className="mb-3"),
                            ], width=12)
                        ]),

                        # Web Server Port
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Web Server Port", className="fw-bold"),
                                dbc.Input(
                                    id="web-server-port-input",
                                    type="number",
                                    min=7000,
                                    max=7999,
                                    value=7500,
                                    className="mb-3"
                                ),
                                html.Small("Port range: 7000-7999. Restart required to apply.", className="text-muted"),
                            ], width=12, md=6)
                        ]),

                        # Log Level
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Log Level", className="fw-bold"),
                                dcc.Dropdown(
                                    id="log-level-dropdown",
                                    options=[
                                        {"label": "DEBUG", "value": "DEBUG"},
                                        {"label": "INFO", "value": "INFO"},
                                        {"label": "WARNING", "value": "WARNING"},
                                        {"label": "ERROR", "value": "ERROR"},
                                    ],
                                    value="INFO",
                                    className="mb-3"
                                ),
                            ], width=12, md=6)
                        ]),

                        # Save Button
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "Save Settings",
                                    id="save-settings-button",
                                    color="primary",
                                    size="lg",
                                    className="mt-3"
                                ),
                            ], width=12)
                        ]),

                        # Status Message
                        html.Div(id="settings-save-status", className="mt-3"),
                    ])
                ], style=CARD_STYLE)
            ], width=12, className="mb-4")
        ]),

        # Section 3: Manual Operations
        html.Hr(),
        html.H3("Manual Operations", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("System Operations", style={"backgroundColor": "#0066cc", "color": "white", "fontWeight": "bold"}),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "Force Aggregation Now",
                                    id="force-aggregation-button",
                                    color="info",
                                    className="w-100 mb-2"
                                ),
                                dbc.Tooltip(
                                    "Manually trigger hourly/daily aggregation",
                                    target="force-aggregation-button",
                                    placement="top"
                                ),
                            ], width=12, md=6, lg=3, className="mb-3"),

                            dbc.Col([
                                dbc.Button(
                                    "Clear Old Samples",
                                    id="clear-samples-button",
                                    color="warning",
                                    className="w-100 mb-2"
                                ),
                                dbc.Tooltip(
                                    "Remove samples older than retention period",
                                    target="clear-samples-button",
                                    placement="top"
                                ),
                            ], width=12, md=6, lg=3, className="mb-3"),

                            dbc.Col([
                                dbc.Button(
                                    "Refresh Cache",
                                    id="refresh-cache-button",
                                    color="secondary",
                                    className="w-100 mb-2"
                                ),
                                dbc.Tooltip(
                                    "Clear internal caches and reload",
                                    target="refresh-cache-button",
                                    placement="top"
                                ),
                            ], width=12, md=6, lg=3, className="mb-3"),

                            dbc.Col([
                                dbc.Button(
                                    "Export Data",
                                    id="export-data-button",
                                    color="success",
                                    className="w-100 mb-2"
                                ),
                                dbc.Tooltip(
                                    "Download database as JSON",
                                    target="export-data-button",
                                    placement="top"
                                ),
                            ], width=12, md=6, lg=3, className="mb-3"),
                        ]),

                        # Operations Status
                        html.Div(id="operations-status", className="mt-3"),
                    ])
                ], style=CARD_STYLE)
            ], width=12, className="mb-4")
        ]),

    ], style=CONTAINER_STYLE)
