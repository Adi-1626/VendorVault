"""
Enterprise Analytics Dashboard UI.
Professional PySide6 dashboard with filter bar, KPI cards, and tabbed analytics.
Version: 2.0.0 | Created: January 2026
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QTabWidget,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QColor, QBrush
from datetime import datetime, timedelta

from src.logic.analytics_engine import AnalyticsEngine, DateRange, KPICalculator
from src.logic.chart_builder import ChartBuilder, ChartTheme


# =============================================================================
# THEME CONSTANTS
# =============================================================================

BG_DARK = '#0F172A'
BG_CARD = '#1E293B'
BORDER = '#334155'
TEXT_PRIMARY = '#F8FAFC'
TEXT_SECONDARY = '#CBD5E1'  # Lighter for better readability
PRIMARY = '#3B82F6'
SUCCESS = '#22C55E'
WARNING = '#F59E0B'
DANGER = '#EF4444'
PURPLE = '#8B5CF6'

# Layout constants
SPACING_SECTION = 24
SPACING_CARD = 16
PADDING_CARD = 16
MIN_CHART_HEIGHT = 360  # Increased for safe text margins
MAX_TABLE_HEIGHT = 240


# =============================================================================
# SMOOTH SCROLL AREA (Fixes wheel freeze)
# =============================================================================

class SmoothScrollArea(QScrollArea):
    """Custom scroll area with smooth mouse wheel handling."""
    
    def wheelEvent(self, event):
        """Handle wheel events for smooth scrolling."""
        if self.verticalScrollBar().isVisible():
            # Smooth scroll by reducing delta
            delta = event.angleDelta().y() // 2
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta
            )
            event.accept()
        else:
            super().wheelEvent(event)


# =============================================================================
# KPI CARD WIDGET
# =============================================================================

class KPICard(QFrame):
    """KPI card with value and change indicator."""
    
    def __init__(self, title: str, value: str, change: float = None, 
                 color: str = PRIMARY, prefix: str = "", parent=None):
        super().__init__(parent)
        self.setup_ui(title, value, change, color, prefix)
    
    def setup_ui(self, title: str, value: str, change: float, color: str, prefix: str):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 2px solid {BORDER};
                border-left: 4px solid {color};
                border-radius: 10px;
            }}
        """)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(6)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 500; border: none;")
        layout.addWidget(title_label)
        
        # Value row
        value_row = QHBoxLayout()
        value_row.setSpacing(8)
        
        value_label = QLabel(f"{prefix}{value}")
        value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; border: none;")
        value_row.addWidget(value_label)
        
        # Change indicator
        if change is not None:
            change_color = SUCCESS if change >= 0 else DANGER
            arrow = "↑" if change >= 0 else "↓"
            change_label = QLabel(f"{arrow} {abs(change):.1f}%")
            change_label.setStyleSheet(f"""
                color: {change_color}; font-size: 12px; font-weight: bold;
                background: {change_color}20; padding: 3px 8px; 
                border-radius: 4px; border: none;
            """)
            value_row.addWidget(change_label)
        
        value_row.addStretch()
        layout.addLayout(value_row)
        layout.addStretch()
    
    def update_value(self, value: str, change: float = None, prefix: str = ""):
        """Update the KPI value and change indicator."""
        # This would require storing references - simplified for now
        pass


# =============================================================================
# FILTER BAR WIDGET
# =============================================================================

class FilterBar(QFrame):
    """Filter bar with date range, product type, and brand filters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.on_filter_changed = None  # Callback
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QComboBox {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                selection-background-color: {PRIMARY};
            }}
            QDateEdit {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Date Range
        date_layout = QVBoxLayout()
        date_layout.setSpacing(4)
        date_label = QLabel("Date Range")
        self.date_combo = QComboBox()
        self.date_combo.addItems(["Last 7 Days", "Last 30 Days", "Last 90 Days", 
                                   "This Month", "This Year", "Custom"])
        self.date_combo.setCurrentIndex(1)  # Default to 30 days
        self.date_combo.currentTextChanged.connect(self._on_date_changed)
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_combo)
        layout.addLayout(date_layout)
        
        # Custom date pickers (hidden by default)
        self.custom_container = QWidget()
        custom_layout = QHBoxLayout(self.custom_container)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(8)
        
        start_layout = QVBoxLayout()
        start_layout.setSpacing(4)
        start_label = QLabel("From")
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_date)
        custom_layout.addLayout(start_layout)
        
        end_layout = QVBoxLayout()
        end_layout.setSpacing(4)
        end_label = QLabel("To")
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_date)
        custom_layout.addLayout(end_layout)
        
        self.custom_container.hide()
        layout.addWidget(self.custom_container)
        
        layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._trigger_refresh)
        layout.addWidget(self.refresh_btn)
    
    def _on_date_changed(self, text: str):
        """Handle date range selection change."""
        self.custom_container.setVisible(text == "Custom")
        if text != "Custom":
            self._trigger_refresh()
    
    def _trigger_refresh(self):
        """Trigger filter change callback."""
        if self.on_filter_changed:
            self.on_filter_changed(self.get_filters())
    
    def get_filters(self) -> dict:
        """Get current filter values."""
        text = self.date_combo.currentText()
        
        preset_map = {
            "Last 7 Days": "7D",
            "Last 30 Days": "30D",
            "Last 90 Days": "90D",
            "This Month": "MTD",
            "This Year": "YTD",
            "Custom": "CUSTOM"
        }
        
        result = {
            'date_range': preset_map.get(text, "30D"),
            'custom_start': None,
            'custom_end': None
        }
        
        if text == "Custom":
            result['custom_start'] = self.start_date.date().toString("yyyy-MM-dd")
            result['custom_end'] = self.end_date.date().toString("yyyy-MM-dd")
        
        return result


# =============================================================================
# DATA TABLE WIDGET
# =============================================================================

class DataTable(QTableWidget):
    """Styled data table with readable white text."""
    
    def __init__(self, headers: list, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self._headers = headers
        self.setup_style()
    
    def setup_style(self):
        self.setStyleSheet(f"""
            QTableWidget, QTableView {{
                background-color: {BG_CARD};
                alternate-background-color: #273449;
                color: {TEXT_PRIMARY};
                gridline-color: {BORDER};
                font-size: 10.5pt;
                border: 2px solid {BORDER};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                font-weight: bold;
                border: 1px solid {BORDER};
                padding: 8px;
                font-size: 11pt;
            }}
            QTableWidget::item {{
                color: {TEXT_PRIMARY};
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {PRIMARY};
                color: #ffffff;
            }}
            QTableWidget::item:hover {{
                background-color: {BORDER};
            }}
        """)
        # Column resize modes
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Row settings
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(36)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setWordWrap(True)
    
    def populate(self, data: list, columns: list):
        """Populate table with data and explicit text colors."""
        self.setRowCount(len(data))
        white_brush = QBrush(QColor(TEXT_PRIMARY))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, col_key in enumerate(columns):
                value = row_data.get(col_key, "")
                
                # Format values
                if isinstance(value, float):
                    if col_key in ['revenue', 'profit', 'cost', 'stock_value', 'avg_unit_cost']:
                        value = f"₹{value:,.2f}"
                    elif col_key in ['margin_percent']:
                        value = f"{value:.1f}%"
                    else:
                        value = f"{value:.2f}"
                
                item = QTableWidgetItem(str(value))
                
                # Force white text color
                item.setForeground(white_brush)
                
                # Column alignment
                if col_idx == 0:  # First column (product name)
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif col_key in ['quantity', 'stock_quantity', 'product_count']:
                    item.setTextAlignment(Qt.AlignCenter)
                elif col_key in ['revenue', 'profit', 'cost', 'avg_unit_cost']:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                
                self.setItem(row_idx, col_idx, item)


# =============================================================================
# ANALYTICS TAB WIDGETS
# =============================================================================

class SalesTab(QWidget):
    """Sales analytics tab with grid layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.charts = ChartBuilder()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, SPACING_CARD, 0, SPACING_CARD)
        layout.setSpacing(SPACING_SECTION)
        
        # Grid for charts
        chart_grid = QGridLayout()
        chart_grid.setSpacing(SPACING_CARD)
        
        # Row 0: Revenue Trend (full width - spans 2 columns)
        self.trend_container = self._create_chart_container()
        self.trend_layout = QVBoxLayout(self.trend_container)
        self.trend_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.trend_container, 0, 0, 1, 2)  # span 2 cols
        
        # Row 1: Sales by Type | Sales by Brand
        self.type_container = self._create_chart_container()
        self.type_layout = QVBoxLayout(self.type_container)
        self.type_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.type_container, 1, 0)
        
        self.brand_container = self._create_chart_container()
        self.brand_layout = QVBoxLayout(self.brand_container)
        self.brand_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.brand_container, 1, 1)
        
        # Row 2: Top Products (full width)
        self.top_container = self._create_chart_container()
        self.top_layout = QVBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.top_container, 2, 0, 1, 2)  # span 2 cols
        
        layout.addLayout(chart_grid)
        
        # Table section with header
        table_section = QVBoxLayout()
        table_section.setSpacing(8)
        
        table_label = QLabel("📊 Product Performance")
        table_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        table_section.addWidget(table_label)
        
        self.products_table = DataTable(["Product", "Qty Sold", "Revenue"])
        self.products_table.setMinimumHeight(150)
        self.products_table.setMaximumHeight(MAX_TABLE_HEIGHT)
        table_section.addWidget(self.products_table)
        
        layout.addLayout(table_section)
    
    def _create_chart_container(self) -> QFrame:
        """Create a styled chart container."""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        container.setMinimumHeight(MIN_CHART_HEIGHT)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return container
    
    def update_data(self, data: dict):
        """Update tab with new data."""
        # Clear existing charts
        self._clear_layout(self.trend_layout)
        self._clear_layout(self.type_layout)
        self._clear_layout(self.brand_layout)
        self._clear_layout(self.top_layout)
        
        # Revenue trend
        trend_title = QLabel("📈 Revenue Trend")
        trend_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.trend_layout.addWidget(trend_title)
        trend_chart = self.charts.build_revenue_trend(data.get('trend', []))
        self.trend_layout.addWidget(trend_chart)
        
        # Sales by type
        type_title = QLabel("📂 Sales by Type")
        type_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.type_layout.addWidget(type_title)
        type_chart = self.charts.build_sales_by_type(data.get('by_type', []))
        self.type_layout.addWidget(type_chart)
        
        # Sales by brand
        brand_title = QLabel("🏷️ Sales by Brand")
        brand_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.brand_layout.addWidget(brand_title)
        brand_chart = self.charts.build_sales_by_brand(data.get('by_brand', []))
        self.brand_layout.addWidget(brand_chart)
        
        # Top products chart
        top_title = QLabel("🏆 Top Products")
        top_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.top_layout.addWidget(top_title)
        top_chart = self.charts.build_top_products_chart(data.get('top_products', []))
        self.top_layout.addWidget(top_chart)
        
        # Products table
        products = data.get('top_products', [])
        self.products_table.populate(products, ['product_name', 'quantity', 'revenue'])
    
    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class InventoryTab(QWidget):
    """Inventory analytics tab with grid layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.charts = ChartBuilder()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, SPACING_CARD, 0, SPACING_CARD)
        layout.setSpacing(SPACING_SECTION)
        
        # Grid for charts
        chart_grid = QGridLayout()
        chart_grid.setSpacing(SPACING_CARD)
        
        # Row 0: Stock Status | Stock Distribution
        self.status_container = self._create_chart_container()
        self.status_layout = QVBoxLayout(self.status_container)
        self.status_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.status_container, 0, 0)
        
        self.dist_container = self._create_chart_container()
        self.dist_layout = QVBoxLayout(self.dist_container)
        self.dist_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.dist_container, 0, 1)
        
        layout.addLayout(chart_grid)
        
        # Table section
        table_section = QVBoxLayout()
        table_section.setSpacing(8)
        
        table_label = QLabel("⚠️ Low Stock Alerts")
        table_label.setStyleSheet(f"color: {DANGER}; font-size: 15px; font-weight: bold;")
        table_section.addWidget(table_label)
        
        self.low_stock_table = DataTable(["Product", "Variant", "Stock", "Reorder", "Status"])
        self.low_stock_table.setMinimumHeight(150)
        self.low_stock_table.setMaximumHeight(MAX_TABLE_HEIGHT + 30)
        table_section.addWidget(self.low_stock_table)
        
        layout.addLayout(table_section)
    
    def _create_chart_container(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        container.setMinimumHeight(MIN_CHART_HEIGHT)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return container
    
    def update_data(self, data: dict):
        """Update tab with new data."""
        self._clear_layout(self.status_layout)
        self._clear_layout(self.dist_layout)
        
        # Stock status
        status_title = QLabel("📊 Stock Status")
        status_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.status_layout.addWidget(status_title)
        status_chart = self.charts.build_stock_status_bars(data.get('kpis', {}))
        self.status_layout.addWidget(status_chart)
        
        # Distribution
        dist_title = QLabel("📦 Stock Distribution")
        dist_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.dist_layout.addWidget(dist_title)
        dist_chart = self.charts.build_stock_distribution_pie(data.get('by_type', []))
        self.dist_layout.addWidget(dist_chart)
        
        # Low stock table
        low_stock = data.get('low_stock', [])
        self.low_stock_table.populate(
            low_stock, 
            ['product_name', 'variant_name', 'stock_quantity', 'reorder_level', 'stock_status']
        )
    
    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class ProfitabilityTab(QWidget):
    """Profitability analytics tab with grid layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.charts = ChartBuilder()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, SPACING_CARD, 0, SPACING_CARD)
        layout.setSpacing(SPACING_SECTION)
        
        # Grid for charts
        chart_grid = QGridLayout()
        chart_grid.setSpacing(SPACING_CARD)
        
        # Row 0: Profit by Product | Profit by Category
        self.product_container = self._create_chart_container()
        self.product_layout = QVBoxLayout(self.product_container)
        self.product_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.product_container, 0, 0)
        
        self.category_container = self._create_chart_container()
        self.category_layout = QVBoxLayout(self.category_container)
        self.category_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.category_container, 0, 1)
        
        layout.addLayout(chart_grid)
        
        # Table section
        table_section = QVBoxLayout()
        table_section.setSpacing(8)
        
        table_label = QLabel("💰 Profit Analysis")
        table_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        table_section.addWidget(table_label)
        
        self.profit_table = DataTable(["Product", "Revenue", "Cost", "Profit", "Margin"])
        self.profit_table.setMinimumHeight(150)
        self.profit_table.setMaximumHeight(MAX_TABLE_HEIGHT)
        table_section.addWidget(self.profit_table)
        
        layout.addLayout(table_section)
    
    def _create_chart_container(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        container.setMinimumHeight(MIN_CHART_HEIGHT)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return container
    
    def update_data(self, data: dict):
        """Update tab with new data."""
        self._clear_layout(self.product_layout)
        self._clear_layout(self.category_layout)
        
        # Profit by product
        prod_title = QLabel("💰 Profit by Product")
        prod_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.product_layout.addWidget(prod_title)
        prod_chart = self.charts.build_profit_by_product(data.get('by_product', []))
        self.product_layout.addWidget(prod_chart)
        
        # Profit by category
        cat_title = QLabel("📂 Profit by Category")
        cat_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.category_layout.addWidget(cat_title)
        cat_chart = self.charts.build_profit_by_category(data.get('by_category', []))
        self.category_layout.addWidget(cat_chart)
        
        # Table
        products = data.get('by_product', [])
        self.profit_table.populate(
            products,
            ['product_name', 'revenue', 'cost', 'profit', 'margin_percent']
        )
    
    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class SupplierTab(QWidget):
    """Supplier analytics tab with grid layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.charts = ChartBuilder()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, SPACING_CARD, 0, SPACING_CARD)
        layout.setSpacing(SPACING_SECTION)
        
        # Grid for charts
        chart_grid = QGridLayout()
        chart_grid.setSpacing(SPACING_CARD)
        
        # Row 0: Products per Supplier | Lead Times
        self.perf_container = self._create_chart_container()
        self.perf_layout = QVBoxLayout(self.perf_container)
        self.perf_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.perf_container, 0, 0)
        
        self.lead_container = self._create_chart_container()
        self.lead_layout = QVBoxLayout(self.lead_container)
        self.lead_layout.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD)
        chart_grid.addWidget(self.lead_container, 0, 1)
        
        layout.addLayout(chart_grid)
        
        # Table section
        table_section = QVBoxLayout()
        table_section.setSpacing(8)
        
        table_label = QLabel("🏭 Supplier Performance")
        table_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        table_section.addWidget(table_label)
        
        self.supplier_table = DataTable(["Supplier", "Products", "Avg Cost", "Lead Time", "Rating"])
        self.supplier_table.setMinimumHeight(150)
        self.supplier_table.setMaximumHeight(MAX_TABLE_HEIGHT)
        table_section.addWidget(self.supplier_table)
        
        layout.addLayout(table_section)
    
    def _create_chart_container(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        container.setMinimumHeight(MIN_CHART_HEIGHT)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return container
    
    def update_data(self, data: dict):
        """Update tab with new data."""
        self._clear_layout(self.perf_layout)
        self._clear_layout(self.lead_layout)
        
        performance = data.get('performance', [])
        
        # Performance chart
        perf_title = QLabel("📊 Products per Supplier")
        perf_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.perf_layout.addWidget(perf_title)
        perf_chart = self.charts.build_supplier_performance(performance)
        self.perf_layout.addWidget(perf_chart)
        
        # Lead time chart
        lead_title = QLabel("⏱️ Lead Times")
        lead_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        self.lead_layout.addWidget(lead_title)
        lead_chart = self.charts.build_lead_time_chart(performance)
        self.lead_layout.addWidget(lead_chart)
        
        # Table
        self.supplier_table.populate(
            performance,
            ['supplier_name', 'product_count', 'avg_unit_cost', 'avg_lead_time', 'rating']
        )
    
    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


# =============================================================================
# MAIN DASHBOARD WINDOW
# =============================================================================

class EnterpriseDashboard(QMainWindow):
    """
    Enterprise Analytics Dashboard with lazy loading and cached data.
    Professional KPI-driven analytics with tabbed modules.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = AnalyticsEngine()
        self.charts = ChartBuilder()
        self.current_filters = {'date_range': '30D', 'custom_start': None, 'custom_end': None}
        
        # Data cache for lazy loading
        self._data_cache = {}
        self._tabs_loaded = {0: False, 1: False, 2: False, 3: False}
        
        self.setup_ui()
        # Defer initial load to after UI is ready
        QTimer.singleShot(100, self._initial_load)
    
    def setup_ui(self):
        """Set up the dashboard UI."""
        self.setWindowTitle("Enterprise Analytics Dashboard")
        self.showMaximized()
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {BG_DARK};
            }}
            QTabBar::tab {{
                background-color: {BG_CARD};
                color: {TEXT_SECONDARY};
                padding: 12px 25px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {PRIMARY};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {BORDER};
            }}
            QScrollArea {{
                border: none;
                background-color: {BG_DARK};
            }}
        """)
        
        # Main scroll area with smooth scrolling
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📊 Enterprise Analytics")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        # Back button
        back_btn = QPushButton("← Back to Dashboard")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {BORDER};
            }}
        """)
        back_btn.clicked.connect(self.close)
        header.addWidget(back_btn)
        
        main_layout.addLayout(header)
        
        # Filter bar
        self.filter_bar = FilterBar()
        self.filter_bar.on_filter_changed = self.on_filter_changed
        main_layout.addWidget(self.filter_bar)
        
        # KPI Cards row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(15)
        main_layout.addLayout(self.kpi_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        
        self.sales_tab = SalesTab()
        self.inventory_tab = InventoryTab()
        self.profitability_tab = ProfitabilityTab()
        self.supplier_tab = SupplierTab()
        
        self.tabs.addTab(self.sales_tab, "📈 Sales")
        self.tabs.addTab(self.inventory_tab, "📦 Inventory")
        self.tabs.addTab(self.profitability_tab, "💰 Profitability")
        self.tabs.addTab(self.supplier_tab, "🏭 Suppliers")
        
        main_layout.addWidget(self.tabs)
        
        # Connect tab change for lazy loading
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        scroll.setWidget(central)
        self.setCentralWidget(scroll)
    
    def _initial_load(self):
        """Initial data load after UI is ready."""
        self.load_kpis_only()
        self._load_current_tab()
    
    def _on_tab_changed(self, index: int):
        """Load tab data lazily when tab is selected."""
        if not self._tabs_loaded.get(index, False):
            self._load_tab_data(index)
    
    def _load_current_tab(self):
        """Load data for currently visible tab."""
        self._load_tab_data(self.tabs.currentIndex())
    
    def on_filter_changed(self, filters: dict):
        """Handle filter changes."""
        self.current_filters = filters
        self.load_data()
    
    def load_kpis_only(self):
        """Load only KPI cards (fast operation)."""
        date_range = self.current_filters.get('date_range', '30D')
        custom_start = self.current_filters.get('custom_start')
        custom_end = self.current_filters.get('custom_end')
        self.load_kpis(date_range, custom_start, custom_end)
    
    def _load_tab_data(self, index: int):
        """Load data for a specific tab."""
        date_range = self.current_filters.get('date_range', '30D')
        custom_start = self.current_filters.get('custom_start')
        custom_end = self.current_filters.get('custom_end')
        
        try:
            if index == 0:  # Sales
                if 'sales' not in self._data_cache:
                    self._data_cache['sales'] = self.engine.get_sales_analytics(date_range, custom_start, custom_end)
                self.sales_tab.update_data(self._data_cache['sales'])
            elif index == 1:  # Inventory
                if 'inventory' not in self._data_cache:
                    self._data_cache['inventory'] = self.engine.get_inventory_analytics()
                self.inventory_tab.update_data(self._data_cache['inventory'])
            elif index == 2:  # Profitability
                if 'profit' not in self._data_cache:
                    self._data_cache['profit'] = self.engine.get_profitability_analytics(date_range, custom_start, custom_end)
                self.profitability_tab.update_data(self._data_cache['profit'])
            elif index == 3:  # Suppliers
                if 'supplier' not in self._data_cache:
                    self._data_cache['supplier'] = self.engine.get_supplier_analytics()
                self.supplier_tab.update_data(self._data_cache['supplier'])
            
            self._tabs_loaded[index] = True
        except Exception as e:
            print(f"Error loading tab {index}: {e}")
    
    def load_data(self):
        """Load all analytics data (called on filter change)."""
        # Clear cache on filter change
        self._data_cache.clear()
        self._tabs_loaded = {0: False, 1: False, 2: False, 3: False}
        
        # Load KPIs immediately
        self.load_kpis_only()
        
        # Load current tab data
        self._load_current_tab()
    
    def load_kpis(self, date_range: str, custom_start: str, custom_end: str):
        """Load and display KPI cards."""
        # Clear existing
        while self.kpi_layout.count():
            child = self.kpi_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        try:
            kpis = self.engine.get_dashboard_kpis(date_range, custom_start, custom_end)
            sales = kpis.get('sales', {})
            inventory = kpis.get('inventory', {})
            profit = kpis.get('profitability', {})
            
            # Revenue
            self.kpi_layout.addWidget(KPICard(
                "Total Revenue",
                f"{sales.get('total_revenue', 0):,.0f}",
                sales.get('revenue_change'),
                SUCCESS, "₹"
            ))
            
            # AOV
            self.kpi_layout.addWidget(KPICard(
                "Avg Order Value",
                f"{sales.get('avg_order_value', 0):,.0f}",
                sales.get('aov_change'),
                PRIMARY, "₹"
            ))
            
            # Bills
            self.kpi_layout.addWidget(KPICard(
                "Total Bills",
                f"{sales.get('bill_count', 0):,}",
                sales.get('bill_change'),
                PURPLE
            ))
            
            # Stock Value
            self.kpi_layout.addWidget(KPICard(
                "Stock Value",
                f"{inventory.get('stock_value', 0):,.0f}",
                None,
                WARNING, "₹"
            ))
            
            # Margin
            self.kpi_layout.addWidget(KPICard(
                "Gross Margin",
                f"{profit.get('margin_percent', 0):.1f}%",
                None,
                SUCCESS if profit.get('margin_percent', 0) >= 20 else WARNING
            ))
            
        except Exception as e:
            # Show error card
            error_label = QLabel(f"Error loading KPIs: {str(e)}")
            error_label.setStyleSheet(f"color: {DANGER}; font-size: 14px;")
            self.kpi_layout.addWidget(error_label)
