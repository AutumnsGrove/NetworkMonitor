"""Tests for the dashboard components and layouts."""

import pytest
from dash import html
import plotly.graph_objects as go


def test_dashboard_imports():
    """Test that all dashboard modules import correctly."""
    from src import dash_app
    from src.dashboard import layouts, components, callbacks, styles

    assert dash_app.app is not None


def test_overview_layout():
    """Test that overview layout renders without errors."""
    from src.dashboard.layouts import overview_layout

    layout = overview_layout()
    assert layout is not None
    # Check that it's a Dash component
    assert hasattr(layout, 'children') or hasattr(layout, '_namespace')


def test_applications_layout():
    """Test that applications layout renders without errors."""
    from src.dashboard.layouts import applications_layout

    layout = applications_layout()
    assert layout is not None
    assert hasattr(layout, 'children') or hasattr(layout, '_namespace')


def test_domains_layout():
    """Test that domains layout renders without errors."""
    from src.dashboard.layouts import domains_layout

    layout = domains_layout()
    assert layout is not None
    assert hasattr(layout, 'children') or hasattr(layout, '_namespace')


def test_history_layout():
    """Test that history layout renders without errors."""
    from src.dashboard.layouts import history_layout

    layout = history_layout()
    assert layout is not None
    assert hasattr(layout, 'children') or hasattr(layout, '_namespace')


def test_config_layout():
    """Test that config layout renders without errors."""
    from src.dashboard.layouts import config_layout

    layout = config_layout()
    assert layout is not None
    assert hasattr(layout, 'children') or hasattr(layout, '_namespace')


def test_component_creation():
    """Test that component helper functions work."""
    from src.dashboard.components import (
        create_stat_card,
        create_gauge_chart,
        create_timeline_chart,
        create_pie_chart,
    )

    # Test stat card
    card = create_stat_card("Test", "100 MB")
    assert card is not None

    # Test gauge chart
    gauge = create_gauge_chart(5.2, max_value=10, title="Test")
    assert gauge is not None
    assert isinstance(gauge, go.Figure)

    # Test timeline chart
    timeline = create_timeline_chart([
        {"timestamp": "2025-01-01T00:00:00", "bytes": 1000}
    ], title="Test")
    assert timeline is not None
    assert isinstance(timeline, go.Figure)

    # Test pie chart
    pie = create_pie_chart([
        {"name": "App1", "bytes": 1000},
        {"name": "App2", "bytes": 2000},
    ], title="Test")
    assert pie is not None
    assert isinstance(pie, go.Figure)


def test_loading_components():
    """Test that loading and error components work."""
    from src.dashboard.components import (
        create_loading_wrapper,
        create_error_alert,
        create_empty_state,
        create_empty_figure_with_message,
    )

    # Test loading wrapper
    test_component = html.Div("Test")
    wrapped = create_loading_wrapper("test-id", test_component)
    assert wrapped is not None

    # Test error alert
    alert = create_error_alert("Test error message", title="Error")
    assert alert is not None

    # Test empty state
    empty = create_empty_state("No data available", icon="📊")
    assert empty is not None

    # Test empty figure
    fig = create_empty_figure_with_message("No data to display")
    assert fig is not None
    assert isinstance(fig, go.Figure)


def test_mock_data_generators():
    """Test that mock data generators work correctly."""
    from src.dashboard.components import (
        generate_mock_heatmap_data,
        generate_mock_weekly_data,
        generate_mock_monthly_data,
    )

    # Test heatmap data
    heatmap = generate_mock_heatmap_data()
    assert len(heatmap) == 7  # 7 days
    assert all(len(day) == 24 for day in heatmap)  # 24 hours each

    # Test weekly data
    weekly = generate_mock_weekly_data()
    assert len(weekly) == 3  # current, last, average
    assert all(len(dataset["x_values"]) == 7 for dataset in weekly)  # 7 days each

    # Test monthly data
    monthly = generate_mock_monthly_data()
    assert len(monthly) == 12  # 12 months


def test_navbar_creation():
    """Test that navbar component is created correctly."""
    from src.dashboard.components import create_navbar

    navbar = create_navbar()
    assert navbar is not None


def test_footer_creation():
    """Test that footer component is created correctly."""
    from src.dashboard.components import create_footer

    footer = create_footer()
    assert footer is not None


def test_chart_with_empty_data():
    """Test that charts handle empty data gracefully."""
    from src.dashboard.components import (
        create_timeline_chart,
        create_pie_chart,
        create_bar_chart,
        create_heatmap,
    )

    # Timeline with empty data
    timeline = create_timeline_chart([], title="Empty Timeline")
    assert timeline is not None
    assert isinstance(timeline, go.Figure)

    # Pie chart with empty data
    pie = create_pie_chart([], title="Empty Pie")
    assert pie is not None
    assert isinstance(pie, go.Figure)

    # Bar chart with empty data
    bar = create_bar_chart({}, "x", "y", "Empty Bar")
    assert bar is not None
    assert isinstance(bar, go.Figure)

    # Heatmap with invalid data
    heatmap_fig = create_heatmap([], title="Empty Heatmap")
    assert heatmap_fig is not None
    assert isinstance(heatmap_fig, go.Figure)


def test_date_utility_functions():
    """Test date utility functions."""
    from src.dashboard.components import (
        get_week_dates,
        get_month_dates,
        format_date_for_api,
    )
    from datetime import datetime, date

    # Test get_week_dates
    start, end = get_week_dates(offset=0)
    assert start is not None
    assert end is not None
    assert start <= end

    # Test get_month_dates
    start, end = get_month_dates(offset=0)
    assert start is not None
    assert end is not None
    assert start <= end

    # Test format_date_for_api
    test_date = date(2025, 1, 15)
    formatted = format_date_for_api(test_date)
    assert formatted == "2025-01-15"

    test_datetime = datetime(2025, 1, 15, 10, 30, 0)
    formatted = format_date_for_api(test_datetime)
    assert formatted == "2025-01-15"


def test_styles_import():
    """Test that styles module imports correctly."""
    from src.dashboard import styles

    # Check color constants exist
    assert hasattr(styles, 'COLORS')
    assert isinstance(styles.COLORS, dict)

    # Check responsive constants exist
    assert hasattr(styles, 'MOBILE_BREAKPOINT')
    assert hasattr(styles, 'TABLET_BREAKPOINT')
    assert hasattr(styles, 'RESPONSIVE_CONTAINER_STYLE')


def test_fetch_api_data_error_handling():
    """Test that fetch_api_data handles errors correctly."""
    from src.dashboard.components import fetch_api_data

    # Test with non-existent endpoint (will fail with connection error)
    result = fetch_api_data("/api/nonexistent")

    # Should return dict with error key
    assert isinstance(result, dict)
    assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
