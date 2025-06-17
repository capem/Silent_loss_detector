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
                            html.H1(
                                "Wind Farm Turbine Investigation",
                                className="text-primary mb-3",
                            ),
                            html.P(
                                "Silent Loss Detection and Analysis Tool",
                                className="lead text-muted",
                            ),
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
                                        html.H4("Data Input", className="mb-0")
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Main data file upload
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Turbine Data File (.pkl)",
                                                        className="form-label",
                                                    ),
                                                    dcc.Upload(
                                                        id="upload-data",
                                                        children=html.Div(
                                                            [
                                                                "Drag and Drop or ",
                                                                html.A(
                                                                    "Select .pkl File"
                                                                ),
                                                            ]
                                                        ),
                                                        style={
                                                            "width": "100%",
                                                            "height": "60px",
                                                            "lineHeight": "60px",
                                                            "borderWidth": "1px",
                                                            "borderStyle": "dashed",
                                                            "borderRadius": "5px",
                                                            "textAlign": "center",
                                                            "margin": "10px 0",
                                                        },
                                                        multiple=False,
                                                    ),
                                                    html.Div(
                                                        id="upload-status",
                                                        className="mt-2",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Optional layout file upload
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Wind Farm Layout (Optional .csv)",
                                                        className="form-label",
                                                    ),
                                                    dcc.Upload(
                                                        id="upload-layout",
                                                        children=html.Div(
                                                            [
                                                                "Drag and Drop or ",
                                                                html.A(
                                                                    "Select Layout CSV"
                                                                ),
                                                            ]
                                                        ),
                                                        style={
                                                            "width": "100%",
                                                            "height": "50px",
                                                            "lineHeight": "50px",
                                                            "borderWidth": "1px",
                                                            "borderStyle": "dashed",
                                                            "borderRadius": "5px",
                                                            "textAlign": "center",
                                                            "margin": "10px 0",
                                                        },
                                                        multiple=False,
                                                    ),
                                                    html.Div(
                                                        id="layout-upload-status",
                                                        className="mt-2",
                                                    ),
                                                ]
                                            ),
                                        ]
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
                                                            html.H4(
                                                                "Data Overview",
                                                                className="mb-0",
                                                            )
                                                        ],
                                                        width=8,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                "📊 Export Data",
                                                                id="export-data-btn",
                                                                color="secondary",
                                                                size="sm",
                                                                outline=True,
                                                            )
                                                        ],
                                                        width=4,
                                                        className="text-end",
                                                    ),
                                                ]
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="data-summary",
                                                children="No data loaded",
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H4("Time Range Filter", className="mb-0")
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Label(
                                                "Select Time Range:",
                                                className="form-label",
                                            ),
                                            dcc.DatePickerRange(
                                                id="date-picker-range",
                                                display_format="YYYY-MM-DD",
                                                style={"width": "100%"},
                                            ),
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Quick Select:",
                                                        className="form-label mt-3",
                                                    ),
                                                    dbc.ButtonGroup(
                                                        [
                                                            dbc.Button(
                                                                "Last 24h",
                                                                id="btn-24h",
                                                                size="sm",
                                                                outline=True,
                                                            ),
                                                            dbc.Button(
                                                                "Last 7d",
                                                                id="btn-7d",
                                                                size="sm",
                                                                outline=True,
                                                            ),
                                                            dbc.Button(
                                                                "Last 30d",
                                                                id="btn-30d",
                                                                size="sm",
                                                                outline=True,
                                                            ),
                                                            dbc.Button(
                                                                "All",
                                                                id="btn-all",
                                                                size="sm",
                                                                outline=True,
                                                            ),
                                                        ],
                                                        className="w-100",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                ],
                className="mb-4",
            ),
            # Operational State Breakdown Table
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(html.H4("Operational State Breakdown", className="mb-0")),
                                dbc.CardBody(
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
                                        style_cell={"textAlign": "left", "padding": "10px", "fontFamily": "Arial"},
                                        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
                                    )
                                ),
                            ]
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
    """Create data summary display."""
    if not summary:
        return [html.P("No data loaded", className="text-muted")]

    time_range = summary.get("time_range", (None, None))
    time_str = "Unknown"
    if time_range[0] and time_range[1]:
        time_str = f"{time_range[0].strftime('%Y-%m-%d %H:%M')} to {time_range[1].strftime('%Y-%m-%d %H:%M')}"

    return [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Strong("Total Records: "),
                        html.Span(f"{summary.get('total_records', 0):,}"),
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        html.Strong("Unique Turbines: "),
                        html.Span(str(summary.get("unique_turbines", 0))),
                    ],
                    width=6,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Strong("Time Range: "),
                        html.Span(time_str, className="small"),
                    ],
                    width=12,
                )
            ],
            className="mt-2",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Strong("Metmast Columns: "),
                        html.Span(str(len(summary.get("metmast_columns", [])))),
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        html.Strong("Layout Data: "),
                        html.Span(
                            "Available"
                            if summary.get("layout_available")
                            else "Not Available"
                        ),
                    ],
                    width=6,
                ),
            ],
            className="mt-2",
        ),
    ]
