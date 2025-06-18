"""
Main dashboard layout for the Wind Farm Turbine Investigation Application.
Module 1: Main Dashboard & Turbine Overview
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from ..utils.config import OPERATIONAL_STATES, TABLE_PAGE_SIZE


def create_main_dashboard_layout():
    """Create the main dashboard layout."""

    return dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.I(
                                                                className="fas fa-wind fa-3x text-primary me-3",
                                                                style={
                                                                    "opacity": "0.8"
                                                                },
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.H1(
                                                                        "Wind Farm Turbine Investigation",
                                                                        className="text-primary mb-2 fw-bold",
                                                                        style={
                                                                            "fontSize": "2.5rem"
                                                                        },
                                                                    ),
                                                                    html.P(
                                                                        "Silent Loss Detection and Analysis Tool",
                                                                        className="lead text-muted mb-0",
                                                                        style={
                                                                            "fontSize": "1.1rem"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        md=8,
                                                        className="d-flex align-items-center",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="py-4",
                                    )
                                ],
                                className="border-0 shadow-sm",
                                style={
                                    "background": "#f8f9fa",  # Light gray background
                                },
                            )
                        ]
                    )
                ],
                className="mb-4",
            ),
            # File Upload Section
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.Div(
                                                [
                                                    html.I(
                                                        className="fas fa-cloud-upload-alt me-2 text-success"
                                                    ),
                                                    html.H4(
                                                        "Data Input",
                                                        className="mb-0 d-inline",
                                                    ),
                                                ],
                                                className="d-flex align-items-center",
                                            )
                                        ],
                                        className="bg-light border-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-database me-1 text-primary"
                                                                    ),
                                                                    "Turbine Data File (.pkl):",
                                                                    html.Span(
                                                                        " *",
                                                                        className="text-danger",
                                                                    ),
                                                                ],
                                                                className="form-label fw-medium mb-2",
                                                            ),
                                                            dcc.Upload(
                                                                id="upload-data",
                                                                children=html.Div(
                                                                    [
                                                                        html.I(
                                                                            className="fas fa-file-upload fa-2x text-primary mb-2"
                                                                        ),
                                                                        html.Br(),
                                                                        "Drag and Drop or ",
                                                                        html.A(
                                                                            "Select .pkl File",
                                                                            className="text-primary fw-medium",
                                                                        ),
                                                                        html.Br(),
                                                                        html.Small(
                                                                            "Supported: .pkl files",
                                                                            className="text-muted",
                                                                        ),
                                                                    ],
                                                                    className="text-center",
                                                                ),
                                                                style={
                                                                    "width": "100%",
                                                                    "height": "120px",
                                                                    "lineHeight": "1.2",
                                                                    "borderWidth": "2px",
                                                                    "borderStyle": "dashed",
                                                                    "borderRadius": "10px",
                                                                    "borderColor": "#007bff",
                                                                    "textAlign": "center",
                                                                    "margin": "10px 0",
                                                                    "padding": "20px",
                                                                    "background": "linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%)",
                                                                    "transition": "all 0.3s ease",
                                                                },
                                                                multiple=False,
                                                            ),
                                                            html.Div(
                                                                id="upload-status",
                                                                className="mt-2",
                                                            ),
                                                        ],
                                                        width=12,
                                                        md=6,
                                                        className="mb-3",
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-map me-1 text-info"
                                                                    ),
                                                                    "Wind Farm Layout (.csv):",
                                                                    html.Span(
                                                                        " (Optional)",
                                                                        className="text-muted small",
                                                                    ),
                                                                ],
                                                                className="form-label fw-medium mb-2",
                                                            ),
                                                            dcc.Upload(
                                                                id="upload-layout",
                                                                children=html.Div(
                                                                    [
                                                                        html.I(
                                                                            className="fas fa-file-csv fa-2x text-info mb-2"
                                                                        ),
                                                                        html.Br(),
                                                                        "Drag and Drop or ",
                                                                        html.A(
                                                                            "Select Layout CSV",
                                                                            className="text-info fw-medium",
                                                                        ),
                                                                        html.Br(),
                                                                        html.Small(
                                                                            "Supported: .csv files",
                                                                            className="text-muted",
                                                                        ),
                                                                    ],
                                                                    className="text-center",
                                                                ),
                                                                style={
                                                                    "width": "100%",
                                                                    "height": "120px",
                                                                    "lineHeight": "1.2",
                                                                    "borderWidth": "2px",
                                                                    "borderStyle": "dashed",
                                                                    "borderRadius": "10px",
                                                                    "borderColor": "#17a2b8",
                                                                    "textAlign": "center",
                                                                    "margin": "10px 0",
                                                                    "padding": "20px",
                                                                    "background": "linear-gradient(135deg, #f0fdff 0%, #ffffff 100%)",
                                                                    "transition": "all 0.3s ease",
                                                                },
                                                                multiple=False,
                                                            ),
                                                            html.Div(
                                                                id="layout-upload-status",
                                                                className="mt-2",
                                                            ),
                                                        ],
                                                        width=12,
                                                        md=6,
                                                        className="mb-3",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="p-4",
                                    ),
                                ]
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Data Summary and Controls
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-chart-bar me-2 text-primary"
                                                                    ),
                                                                    html.H4(
                                                                        "Data Overview",
                                                                        className="mb-0 d-inline",
                                                                    ),
                                                                ],
                                                                className="d-flex align-items-center",
                                                            )
                                                        ],
                                                        width=8,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-download me-1"
                                                                    ),
                                                                    "Export Data",
                                                                ],
                                                                id="export-data-btn",
                                                                color="primary",
                                                                size="sm",
                                                                outline=True,
                                                                className="shadow-sm",
                                                            )
                                                        ],
                                                        width=4,
                                                        className="text-end",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="bg-light border-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="data-summary",
                                                children="No data loaded",
                                            )
                                        ],
                                        className="p-3",
                                    ),
                                ],
                                className="shadow-sm border-0 h-100",
                            )
                        ],
                        width=12,
                        lg=7,
                        className="mb-4",
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.Div(
                                                [
                                                    html.I(
                                                        className="fas fa-calendar-alt me-2 text-info"
                                                    ),
                                                    html.H4(
                                                        "Time Range Filter",
                                                        className="mb-0 d-inline",
                                                    ),
                                                ],
                                                className="d-flex align-items-center",
                                            )
                                        ],
                                        className="bg-light border-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Label(
                                                [
                                                    html.I(
                                                        className="fas fa-calendar me-1 text-muted"
                                                    ),
                                                    "Select Time Range:",
                                                ],
                                                className="form-label fw-medium mb-2",
                                            ),
                                            dcc.DatePickerRange(
                                                id="date-picker-range",
                                                display_format="YYYY-MM-DD",
                                                style={
                                                    "width": "100%",
                                                    "border": "1px solid #dee2e6",
                                                    "borderRadius": "0.375rem",
                                                },
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                [
                                                    html.I(
                                                        className="fas fa-bolt me-1 text-muted"
                                                    ),
                                                    "Quick Select:",
                                                ],
                                                className="form-label fw-medium mb-2",
                                            ),
                                            dbc.ButtonGroup(
                                                [
                                                    dbc.Button(
                                                        "Last 24h",
                                                        id="btn-24h",
                                                        size="sm",
                                                        outline=True,
                                                        color="secondary",
                                                    ),
                                                    dbc.Button(
                                                        "Last 7d",
                                                        id="btn-7d",
                                                        size="sm",
                                                        outline=True,
                                                        color="secondary",
                                                    ),
                                                    dbc.Button(
                                                        "Last 30d",
                                                        id="btn-30d",
                                                        size="sm",
                                                        outline=True,
                                                        color="secondary",
                                                    ),
                                                    dbc.Button(
                                                        "All",
                                                        id="btn-all",
                                                        size="sm",
                                                        outline=True,
                                                        color="primary",
                                                    ),
                                                ],
                                                className="w-100",
                                            ),
                                        ],
                                        className="p-3",
                                    ),
                                ],
                                className="shadow-sm border-0 h-100",
                            )
                        ],
                        width=12,
                        lg=5,
                        className="mb-4",
                    ),
                ]
            ),
            # Operational State Breakdown Table
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.Div(
                                            [
                                                html.I(
                                                    className="fas fa-table me-2 text-warning"
                                                ),
                                                html.H4(
                                                    "Operational State Breakdown",
                                                    className="mb-0 d-inline",
                                                ),
                                            ],
                                            className="d-flex align-items-center",
                                        )
                                    ],
                                    className="bg-light border-0",
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Alert(
                                            [
                                                html.I(
                                                    className="fas fa-info-circle me-2"
                                                ),
                                                "Click on any turbine row to launch detailed investigation analysis.",
                                            ],
                                            color="info",
                                            className="mb-3",
                                            dismissable=True,
                                        ),
                                        dash_table.DataTable(
                                            id="operational-state-breakdown-table",
                                            # Columns will be set dynamically in the callback
                                            data=[],
                                            sort_action="native",
                                            filter_action="native",
                                            page_action="native",
                                            page_current=0,
                                            page_size=TABLE_PAGE_SIZE,
                                            row_selectable="single",
                                            selected_rows=[],
                                            style_cell={
                                                "textAlign": "left",
                                                "padding": "12px",
                                                "fontFamily": "system-ui, -apple-system, sans-serif",
                                                "fontSize": "14px",
                                                "border": "1px solid #dee2e6",
                                            },
                                            style_header={
                                                "backgroundColor": "#f8f9fa",
                                                "fontWeight": "600",
                                                "color": "#495057",
                                                "border": "1px solid #dee2e6",
                                                "textAlign": "center",
                                            },
                                            style_data={
                                                "backgroundColor": "#ffffff",
                                                "color": "#212529",
                                            },
                                            style_data_conditional=[
                                                {
                                                    "if": {"row_index": "odd"},
                                                    "backgroundColor": "#f8f9fa",
                                                },
                                                {
                                                    "if": {"state": "selected"},
                                                    "backgroundColor": "#e3f2fd",
                                                    "border": "2px solid #2196f3",
                                                },
                                            ],
                                            style_table={
                                                "overflowX": "auto",
                                                "border": "1px solid #dee2e6",
                                                "borderRadius": "0.375rem",
                                            },
                                        ),
                                    ],
                                    className="p-3",
                                ),
                            ],
                            className="shadow-sm border-0",
                        ),
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Investigation Panel (Initially Hidden)
            html.Div(id="investigation-panel", children=[], style={"display": "none"}),
            # Store components for data
            dcc.Store(id="data-store"),
            dcc.Store(id="layout-store"),
            dcc.Store(id="filter-params-store"),  # Replaced filtered-data-store
            dcc.Store(id="selected-turbine-store"),
        ],
        fluid=True,
    )


def create_data_summary_display(summary: dict) -> list:
    """Create enhanced data summary display with modern styling."""
    if not summary:
        return [
            dbc.Alert(
                [
                    html.I(className="fas fa-info-circle me-2"),
                    "No data loaded. Please upload a turbine data file to begin analysis.",
                ],
                color="info",
                className="mb-0",
            )
        ]

    time_range = summary.get("time_range", (None, None))
    time_str = "Unknown"
    if time_range[0] and time_range[1]:
        time_str = f"{time_range[0].strftime('%Y-%m-%d %H:%M')} to {time_range[1].strftime('%Y-%m-%d %H:%M')}"

    # Create metric cards
    metrics = [
        {
            "title": "Total Records",
            "value": f"{summary.get('total_records', 0):,}",
            "icon": "fas fa-database",
            "color": "primary",
        },
        {
            "title": "Unique Turbines",
            "value": str(summary.get("unique_turbines", 0)),
            "icon": "fas fa-wind",
            "color": "success",
        },
        {
            "title": "Metmast Columns",
            "value": str(len(summary.get("metmast_columns", []))),
            "icon": "fas fa-chart-line",
            "color": "info",
        },
        {
            "title": "Layout Data",
            "value": "Available"
            if summary.get("layout_available")
            else "Not Available",
            "icon": "fas fa-map"
            if summary.get("layout_available")
            else "fas fa-map-marked-alt",
            "color": "success" if summary.get("layout_available") else "warning",
        },
    ]

    metric_cards = []
    for metric in metrics:
        card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.I(
                                            className=f"{metric['icon']} fa-2x text-{metric['color']}",
                                            style={"opacity": "0.8"},
                                        )
                                    ],
                                    width=3,
                                    className="d-flex align-items-center justify-content-center",
                                ),
                                dbc.Col(
                                    [
                                        html.H4(
                                            metric["value"],
                                            className=f"text-{metric['color']} mb-1 fw-bold",
                                        ),
                                        html.P(
                                            metric["title"],
                                            className="text-muted mb-0 small",
                                        ),
                                    ],
                                    width=9,
                                ),
                            ],
                            className="align-items-center",
                        )
                    ],
                    className="py-2",
                )
            ],
            className="border-0 shadow-sm h-100",
            style={"background": "linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)"},
        )
        metric_cards.append(card)

    return [
        # Metric cards in a responsive grid
        dbc.Row(
            [
                dbc.Col(card, width=12, md=6, lg=3, className="mb-3")
                for card in metric_cards
            ],
            className="mb-3",
        ),
        # Time range info card
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.I(
                                            className="fas fa-clock fa-lg text-secondary me-2"
                                        ),
                                        html.Strong(
                                            "Data Time Range:",
                                            className="text-secondary",
                                        ),
                                    ],
                                    width="auto",
                                    className="d-flex align-items-center",
                                ),
                                dbc.Col(
                                    [
                                        html.Span(
                                            time_str, className="text-dark fw-medium"
                                        )
                                    ],
                                    className="d-flex align-items-center",
                                ),
                            ]
                        )
                    ],
                    className="py-2",
                )
            ],
            className="border-0 shadow-sm",
            style={"background": "linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)"},
        ),
    ]
