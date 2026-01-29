"""
Modern Analytics window with professional visualizations and insights.
"""
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime, timedelta

from src.logic.analytics import AnalyticsService
from src.logic.inventory import InventoryService
from src.logic.billing import BillingService


class ModernAnalyticsWindow(QMainWindow):
    """Modern analytics dashboard with professional visualizations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analytics = AnalyticsService()
        self.inventory = InventoryService()
        self.billing = BillingService()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Analytics & Insights - VendorVault")
        self.showMaximized()
        
        # Dark theme colors
        self.bg_color = "#0F172A"
        self.card_color = "#1E293B"
        self.text_color = "#F8FAFC"
        self.text_gray = "#94A3B8"
        
        # Central widget with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ 
                border: none;
                background-color: {self.bg_color};
            }}
            QWidget {{
                background-color: {self.bg_color};
            }}
            QScrollBar:vertical {{
                background-color: {self.bg_color};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #334155;
                border-radius: 6px;
                min-height: 30px;
            }}
        """)
        
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {self.bg_color};")
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)
        
        # Header
        header = QLabel("Analytics & Business Insights")
        header.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {self.text_color}; margin-bottom: 10px;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Data-driven insights to help you make better business decisions")
        subtitle.setStyleSheet(f"font-size: 18px; color: {self.text_gray}; margin-bottom: 20px;")
        main_layout.addWidget(subtitle)
        
        # Key Metrics Cards
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(20)
        
        try:
            daily_revenue = self.billing.calculate_daily_revenue(datetime.now().strftime("%Y-%m-%d"))
            today_bills = len(self.billing.get_todays_bills())
            total_products = self.inventory.get_total_product_count()
            stock_value = self.inventory.get_total_stock_value()
            
            metrics_layout.addWidget(self.create_metric_card("Today's Revenue", f"₹{daily_revenue:,.2f}", "Sales", "#10B981"))
            metrics_layout.addWidget(self.create_metric_card("Bills Today", str(today_bills), "Transactions", "#2563EB"))
            metrics_layout.addWidget(self.create_metric_card("Total Products", str(total_products), "Inventory", "#8B5CF6"))
            metrics_layout.addWidget(self.create_metric_card("Stock Value", f"₹{stock_value:,.2f}", "Assets", "#F59E0B"))
        except:
            pass
        
        main_layout.addLayout(metrics_layout)
        
        # Charts Grid
        charts_grid = QGridLayout()
        charts_grid.setSpacing(20)
        
        # Row 1: Best Sellers + Revenue Trend
        charts_grid.addWidget(self.create_best_sellers_chart(), 0, 0)
        charts_grid.addWidget(self.create_revenue_trend_chart(), 0, 1)
        
        # Row 2: Category Distribution + Low Stock Alert
        charts_grid.addWidget(self.create_category_distribution_chart(), 1, 0)
        charts_grid.addWidget(self.create_low_stock_chart(), 1, 1)
        
        # Row 3: Profit Analysis + Top Customers
        charts_grid.addWidget(self.create_profit_analysis_chart(), 2, 0)
        charts_grid.addWidget(self.create_sales_by_time_chart(), 2, 1)
        
        main_layout.addLayout(charts_grid)
        
        central_widget.setLayout(main_layout)
        scroll.setWidget(central_widget)
        self.setCentralWidget(scroll)
    
    def create_metric_card(self, title: str, value: str, color: str, subtitle: str) -> QFrame:
        """Create a dark metric card."""
        card = QFrame()
        card.setMinimumHeight(160)
        card.setMaximumHeight(180)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_color};
                border: 2px solid #334155;
                border-left: 4px solid {color};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; color: {self.text_gray}; font-weight: 500; border: none;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {color}; margin: 8px 0px; border: none;")
        layout.addWidget(value_label)
        
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(f"font-size: 13px; color: {self.text_gray}; border: none;")
        layout.addWidget(sub_label)
        
        layout.addStretch()
        card.setLayout(layout)
        return card
    
    def create_chart_container(self, title: str, canvas) -> QFrame:
        """Create a dark container for a chart."""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_color};
                border: 2px solid #334155;
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel(title)
        header.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {self.text_color}; margin-bottom: 10px; border: none;")
        layout.addWidget(header)
        
        layout.addWidget(canvas)
        container.setLayout(layout)
        
        return container
    
    def _setup_dark_chart(self, ax, title, xlabel=None, ylabel=None):
        """Apply professional dark theme to chart axes."""
        ax.set_facecolor('#1E293B')
        ax.set_title(title, fontsize=14, fontweight='600', color='#F8FAFC', pad=15)
        
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=12, color='#94A3B8')
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=12, color='#94A3B8')
            
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#64748B')
        ax.spines['bottom'].set_color('#64748B')
        ax.tick_params(colors='#94A3B8', labelsize=10)
        ax.grid(True, linestyle='--', alpha=0.1, color='white')

    def create_best_sellers_chart(self) -> QFrame:
        """Create best selling products chart."""
        fig = Figure(figsize=(6, 4), facecolor='#1E293B')
        ax = fig.add_subplot(111)
        
        try:
            products = self.analytics.get_best_selling_products('today')
            if products:
                names = [p['product_name'][:15] + '...' if len(p['product_name']) > 15 else p['product_name'] for p in products[:5]]
                quantities = [p['total_quantity'] for p in products[:5]]
                
                # Professional gradient-like colors
                colors = ['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#DBEAFE']
                bars = ax.barh(names, quantities, color=colors, height=0.6)
                
                self._setup_dark_chart(ax, 'Top 5 Best Sellers (Today)', 'Quantity Sold')
                
                # Value labels
                for rect in bars:
                    width = rect.get_width()
                    ax.text(width + 0.5, rect.get_y() + rect.get_height()/2, 
                            f'{int(width)}', ha='left', va='center', color='#F8FAFC', fontweight='bold')
            else:
                self._setup_dark_chart(ax, 'Top 5 Best Sellers (Today)')
                ax.text(0.5, 0.5, 'No sales yet today', ha='center', va='center', transform=ax.transAxes, color='#94A3B8', fontsize=12)
                ax.set_xticks([])
                ax.set_yticks([])
        except Exception as e:
            ax.text(0.5, 0.5, 'Error loading data', ha='center', va='center', transform=ax.transAxes, color='#EF4444')
            ax.axis('off')
        
        fig.tight_layout()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumHeight(300)
        return self.create_chart_container("📊 Best Selling Products", canvas)
    
    def create_revenue_trend_chart(self) -> QFrame:
        """Create revenue trend chart."""
        fig = Figure(figsize=(6, 4), facecolor='#1E293B')
        ax = fig.add_subplot(111)
        
        try:
            dates = []
            revenues = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                revenue = self.billing.calculate_daily_revenue(date)
                dates.append((datetime.now() - timedelta(days=i)).strftime("%d %b"))
                revenues.append(revenue)
            
            self._setup_dark_chart(ax, '7-Day Revenue Trend', ylabel='Revenue (₹)')
            
            if max(revenues) > 0:
                ax.plot(dates, revenues, marker='o', linewidth=2.5, markersize=8,
                       color='#10B981', markerfacecolor='#10B981', markeredgecolor='#ECFDF5', markeredgewidth=2)
                ax.fill_between(dates, revenues, alpha=0.15, color='#10B981')
            else:
                ax.text(0.5, 0.5, 'No revenue data', ha='center', va='center', transform=ax.transAxes, color='#94A3B8', fontsize=12)
                
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        except Exception as e:
            ax.axis('off')
            ax.text(0.5, 0.5, 'Error loading data', ha='center', va='center', transform=ax.transAxes, color='#EF4444')
        
        fig.tight_layout()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumHeight(300)
        return self.create_chart_container("📈 Revenue Trend", canvas)
    
    def create_category_distribution_chart(self) -> QFrame:
        """Create category distribution donut chart."""
        fig = Figure(figsize=(6, 4), facecolor='#1E293B')
        ax = fig.add_subplot(111)
        
        try:
            categories = self.inventory.get_categories() or []
            cat_counts = {}
            for cat in categories:
                products = self.inventory.get_products_by_category(cat, None)
                if products:
                    cat_counts[cat] = len(products)
            
            if cat_counts:
                colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
                wedges, texts, autotexts = ax.pie(cat_counts.values(), labels=cat_counts.keys(),
                                                   autopct='%1.1f%%', colors=colors[:len(cat_counts)],
                                                   startangle=90, pctdistance=0.85, 
                                                   textprops={'color': '#F8FAFC', 'fontsize': 10},
                                                   wedgeprops=dict(width=0.4, edgecolor='#1E293B'))
                
                # Make it a professional donut chart
                ax.set_title('Product Categories', fontsize=14, fontweight='600', color='#F8FAFC', pad=15)
                
                # Center text
                total = sum(cat_counts.values())
                ax.text(0, 0, f"{total}\nItems", ha='center', va='center', fontsize=12, fontweight='bold', color='#F8FAFC')
            else:
                ax.text(0.5, 0.5, 'No inventory data', ha='center', va='center', transform=ax.transAxes, color='#94A3B8', fontsize=12)
                ax.axis('off')
                
        except Exception as e:
            ax.axis('off')
            
        fig.tight_layout()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumHeight(300)
        return self.create_chart_container("📂 Inventory Mix", canvas)
    
    def create_low_stock_chart(self) -> QFrame:
        """Create low stock alert chart."""
        fig = Figure(figsize=(6, 4), facecolor='#1E293B')
        ax = fig.add_subplot(111)
        
        try:
            low_stock = self.inventory.get_low_stock_products(threshold=20)
            if low_stock:
                names = [p.product_name[:15] for p in low_stock[:8]]
                stocks = [p.stock for p in low_stock[:8]]
                
                colors = ['#EF4444' if s < 10 else '#F59E0B' for s in stocks]
                bars = ax.bar(range(len(names)), stocks, color=colors, edgecolor='none')
                
                ax.set_xticks(range(len(names)))
                ax.set_xticklabels(names, rotation=45, ha='right', fontsize=9)
                ax.set_ylabel('Stock Quantity', fontsize=12, fontweight='500', color='#374151')
                ax.set_title('⚠️ Low Stock Alert', fontsize=14, fontweight='600', pad=15, color='#DC2626')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_color('#E5E7EB')
                ax.spines['bottom'].set_color('#E5E7EB')
                ax.tick_params(colors='#6B7280')
                ax.axhline(y=10, color='#EF4444', linestyle='--', linewidth=1, alpha=0.5, label='Critical (10)')
                ax.grid(axis='y', alpha=0.2, linestyle='--')
                ax.legend(fontsize=9)
                
                for i, (bar, stock) in enumerate(zip(bars, stocks)):
                    ax.text(i, stock + 0.5, str(stock), ha='center', fontsize=9, fontweight='600', color='#374151')
            else:
                ax.text(0.5, 0.5, '✓ All products well stocked', ha='center', va='center', transform=ax.transAxes,
                       fontsize=14, color='#10B981', fontweight='600')
                ax.axis('off')
        except Exception as e:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes,
                   fontsize=14, color='#9CA3AF')
            ax.axis('off')
        
        fig.tight_layout()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumHeight(300)
        
        return self.create_chart_container("⚠️ Stock Alerts", canvas)
    
    def create_profit_analysis_chart(self) -> QFrame:
        """Create profit analysis chart."""
        fig = Figure(figsize=(6, 4), facecolor='#1E293B')
        ax = fig.add_subplot(111)
        
        try:
            profit_data = self.analytics.calculate_profit_by_product('today')
            if profit_data:
                items = [(p['product_name'][:12], p['profit']) for p in profit_data[:6]]
                names = [item[0] for item in items]
                profits = [item[1] for item in items]
                
                colors = ['#10B981' if p > 0 else '#EF4444' for p in profits]
                bars = ax.barh(names, profits, color=colors, edgecolor='none')
                
                ax.set_xlabel('Profit (₹)', fontsize=12, fontweight='500', color='#374151')
                ax.set_title('💰 Profit by Product - Today', fontsize=14, fontweight='600', pad=15)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_color('#E5E7EB')
                ax.spines['bottom'].set_color('#E5E7EB')
                ax.tick_params(colors='#6B7280')
                ax.axvline(x=0, color='#6B7280', linestyle='-', linewidth=1)
                ax.grid(axis='x', alpha=0.2, linestyle='--')
                
                for i, (bar, profit) in enumerate(zip(bars, profits)):
                    ax.text(profit + (5 if profit > 0 else -5), i, f'₹{profit:.0f}',
                           va='center', ha='left' if profit > 0 else 'right',
                           fontsize=9, fontweight='600', color='#374151')
            else:
                ax.text(0.5, 0.5, 'No profit data', ha='center', va='center', transform=ax.transAxes,
                       fontsize=14, color='#9CA3AF')
                ax.axis('off')
        except Exception as e:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes,
                   fontsize=14, color='#9CA3AF')
            ax.axis('off')
        
        fig.tight_layout()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumHeight(300)
        
        return self.create_chart_container("💰 Profit Analysis", canvas)
    
    def create_sales_by_time_chart(self) -> QFrame:
        """Create sales by time of day chart."""
        fig = Figure(figsize=(6, 4), facecolor='#1E293B')
        ax = fig.add_subplot(111)
        
        # Placeholder data - could be enhanced with real time-based data
        ax.text(0.5, 0.5, 'Time-based analytics\n(Coming soon)', ha='center', va='center',
               transform=ax.transAxes, fontsize=14, color='#9CA3AF')
        ax.axis('off')
        
        fig.tight_layout()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumHeight(300)
        
        return self.create_chart_container("🕐 Sales by Time", canvas)
