"""
Chart Builder for Enterprise Analytics Dashboard.
Professional Matplotlib chart rendering with dark theme.
Version: 2.0.0 | Created: January 2026
"""
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime

# =============================================================================
# DARK THEME CONFIGURATION
# =============================================================================

class ChartTheme:
    """Professional dark theme for charts with safe text rendering."""
    
    # Colors
    BG_DARK = '#0F172A'
    BG_CARD = '#1E293B'
    TEXT_PRIMARY = '#F8FAFC'
    TEXT_SECONDARY = '#CBD5E1'
    GRID_COLOR = '#334155'
    BORDER_COLOR = '#475569'
    
    # Accent colors
    PRIMARY = '#3B82F6'
    SUCCESS = '#22C55E'
    WARNING = '#F59E0B'
    DANGER = '#EF4444'
    PURPLE = '#8B5CF6'
    CYAN = '#06B6D4'
    PINK = '#EC4899'
    
    # Color palettes
    PALETTE_BARS = ['#3B82F6', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#10B981']
    PALETTE_GRADIENT = ['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#DBEAFE']
    
    # Font sizes (larger for readability)
    FONT_TITLE = 14
    FONT_LABEL = 12
    FONT_TICK = 11
    FONT_VALUE = 11
    
    # Chart dimensions
    MIN_HEIGHT = 320
    MAX_HEIGHT = 420
    
    # Safe margins to prevent clipping (INCREASED)
    MARGIN_LEFT = 0.16
    MARGIN_RIGHT = 0.94
    MARGIN_TOP = 0.86
    MARGIN_BOTTOM = 0.22
    
    @classmethod
    def setup_rcparams(cls):
        """Configure matplotlib rcParams for consistent rendering."""
        import matplotlib
        matplotlib.rcParams.update({
            'axes.titlesize': cls.FONT_TITLE,
            'axes.labelsize': cls.FONT_LABEL,
            'xtick.labelsize': cls.FONT_TICK,
            'ytick.labelsize': cls.FONT_TICK,
            'legend.fontsize': cls.FONT_TICK,
            'figure.autolayout': False,
            'axes.titlepad': 12,
            'axes.labelpad': 10,
        })
    
    @classmethod
    def apply_to_axes(cls, ax, title: str = None, xlabel: str = None, ylabel: str = None):
        """Apply dark theme with improved text visibility."""
        ax.set_facecolor(cls.BG_CARD)
        
        if title:
            ax.set_title(title, fontsize=cls.FONT_TITLE, fontweight='600', 
                        color=cls.TEXT_PRIMARY, pad=14, loc='left')
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=cls.FONT_LABEL, color=cls.TEXT_SECONDARY, labelpad=12)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=cls.FONT_LABEL, color=cls.TEXT_SECONDARY, labelpad=12)
        
        # Spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(cls.BORDER_COLOR)
        ax.spines['bottom'].set_color(cls.BORDER_COLOR)
        
        # Ticks
        ax.tick_params(colors=cls.TEXT_SECONDARY, labelsize=cls.FONT_TICK)
        
        # Grid
        ax.grid(True, linestyle='--', alpha=0.1, color=cls.TEXT_PRIMARY)
        ax.set_axisbelow(True)
    
    @classmethod
    def create_figure(cls, figsize: tuple = (6, 3.8)) -> Figure:
        """Create figure without constrained layout for manual margin control."""
        cls.setup_rcparams()
        fig = Figure(figsize=figsize, facecolor=cls.BG_CARD, dpi=100)
        fig.patch.set_facecolor(cls.BG_CARD)
        return fig
    
    @classmethod
    def finalize_figure(cls, fig, tight: bool = True):
        """Apply safe margins to prevent text clipping."""
        try:
            # Apply subplots_adjust FIRST for consistent margins
            fig.subplots_adjust(
                left=cls.MARGIN_LEFT, 
                right=cls.MARGIN_RIGHT, 
                top=cls.MARGIN_TOP, 
                bottom=cls.MARGIN_BOTTOM
            )
            # tight_layout can override, use large pad
            if tight:
                fig.tight_layout(pad=3.0, rect=[0.02, 0.02, 0.98, 0.96])
        except Exception:
            pass
    
    @classmethod
    def wrap_text(cls, text: str, max_chars: int = 15) -> str:
        """Wrap long text with line breaks."""
        if len(text) <= max_chars:
            return text
        words = text.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return "\n".join(lines[:2])  # Max 2 lines


# =============================================================================
# CHART BUILDER CLASS
# =============================================================================

class ChartBuilder:
    """
    Professional chart builder for analytics dashboard.
    All methods return FigureCanvas for embedding in PySide6.
    """
    
    def __init__(self):
        self.theme = ChartTheme
    
    # =========================================================================
    # SALES CHARTS
    # =========================================================================
    
    def build_revenue_trend(self, data: List[Dict], title: str = "Revenue Trend") -> FigureCanvas:
        """
        Build revenue trend line chart.
        
        Args:
            data: List of dicts with 'sale_date' and 'total_revenue'
        """
        fig = self.theme.create_figure(figsize=(8, 3.2))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, ylabel='Revenue (₹)')
        
        if not data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            df = pd.DataFrame(data)
            if 'sale_date' in df.columns:
                dates = pd.to_datetime(df['sale_date'])
                values = df['total_revenue'].values
                
                # Plot line with gradient fill
                ax.plot(dates, values, marker='o', linewidth=2.5, markersize=7,
                        color=self.theme.SUCCESS, markerfacecolor=self.theme.SUCCESS,
                        markeredgecolor='white', markeredgewidth=1.5)
                ax.fill_between(dates, values, alpha=0.15, color=self.theme.SUCCESS)
                
                # Format x-axis
                ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d %b'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha='right', fontsize=9)
                
                # Format y-axis with currency
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
                
                # Value labels on points (only if few points)
                if len(values) <= 10:
                    for i, (d, v) in enumerate(zip(dates, values)):
                        if v > 0:
                            ax.annotate(f'₹{v:,.0f}', (d, v), textcoords='offset points',
                                        xytext=(0, 10), ha='center', fontsize=9,
                                        color=self.theme.TEXT_PRIMARY, fontweight='bold')
        
        self.theme.finalize_figure(fig)
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(340)
        return canvas
    
    def build_sales_by_type(self, data: List[Dict], title: str = "Sales by Product Type") -> FigureCanvas:
        """Build horizontal bar chart for sales by product type."""
        fig = self.theme.create_figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, xlabel='Revenue (₹)')
        
        if not data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            df = pd.DataFrame(data).sort_values('revenue', ascending=True)
            
            categories = df['product_type'].values
            revenues = df['revenue'].values
            
            # Limit to top 5 for better visibility
            if len(categories) > 5:
                categories = categories[-5:]
                revenues = revenues[-5:]
            
            # Truncate long category names
            categories = [self.theme.wrap_text(str(c), 12) for c in categories]
            
            colors = self.theme.PALETTE_BARS[:len(categories)]
            bars = ax.barh(categories, revenues, color=colors, height=0.5, edgecolor='none')
            
            # Value labels with offset
            max_rev = max(revenues) if len(revenues) > 0 else 1
            for bar in bars:
                width = bar.get_width()
                ax.text(width + max_rev * 0.04, bar.get_y() + bar.get_height()/2,
                        f'₹{width:,.0f}', va='center', fontsize=10,
                        color=self.theme.TEXT_PRIMARY, fontweight='bold')
            
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(
                lambda x, p: f'₹{x/1000:.0f}K' if x >= 1000 else f'₹{x:.0f}'))
            ax.set_xlim(0, max_rev * 1.30)  # Extra space for labels
            ax.margins(y=0.1)
        
        self.theme.finalize_figure(fig)
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(340)
        return canvas
    
    def build_sales_by_brand(self, data: List[Dict], title: str = "Sales by Brand") -> FigureCanvas:
        """Build bar chart for sales by brand."""
        fig = self.theme.create_figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, ylabel='Revenue (₹)')
        
        if not data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            df = pd.DataFrame(data).sort_values('revenue', ascending=False)
            
            brands = df['brand_name'].values[:5]  # Limit to 5 for readability
            revenues = df['revenue'].values[:5]
            
            # Truncate long brand names
            brands = [b[:10] + '..' if len(str(b)) > 10 else b for b in brands]
            
            x = np.arange(len(brands))
            bars = ax.bar(x, revenues, color=self.theme.PALETTE_BARS[:len(brands)], 
                          width=0.5, edgecolor='none')
            
            ax.set_xticks(x)
            ax.set_xticklabels(brands, rotation=30, ha='right', fontsize=10)
            
            # Value labels with offset
            max_rev = max(revenues) if len(revenues) > 0 else 1
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height + max_rev * 0.03,
                        f'₹{height:,.0f}', ha='center', va='bottom',
                        fontsize=10, color=self.theme.TEXT_PRIMARY, fontweight='bold')
            
            ax.set_ylim(0, max_rev * 1.20)  # Extra space for labels
            ax.margins(x=0.1)
        
        self.theme.finalize_figure(fig)
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(340)
        return canvas
    
    def build_top_products_chart(self, data: List[Dict], title: str = "Top Products") -> FigureCanvas:
        """Build horizontal bar chart for top products."""
        fig = self.theme.create_figure(figsize=(6, 4.2))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, xlabel='Quantity Sold')
        
        if not data:
            ax.text(0.5, 0.5, 'No sales data', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            # Limit to 6 products and truncate names
            top_data = data[:6]
            names = [self.theme.wrap_text(p['product_name'], 15) for p in top_data]
            quantities = [p['quantity'] for p in top_data]
            
            colors = self.theme.PALETTE_BARS[:len(names)]
            bars = ax.barh(names[::-1], quantities[::-1], color=colors[::-1], height=0.5)
            
            # Value labels with offset
            max_qty = max(quantities) if quantities else 1
            for bar in bars:
                width = bar.get_width()
                ax.text(width + max_qty * 0.04, bar.get_y() + bar.get_height()/2,
                        f'{int(width)}', va='center', fontsize=11,
                        color=self.theme.TEXT_PRIMARY, fontweight='bold')
            
            ax.set_xlim(0, max_qty * 1.25)
            ax.margins(y=0.1)
        
        self.theme.finalize_figure(fig)
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(340)
        return canvas
    
    # =========================================================================
    # INVENTORY CHARTS
    # =========================================================================
    
    def build_stock_distribution_pie(self, data: List[Dict], title: str = "Stock Distribution") -> FigureCanvas:
        """Build donut chart for stock distribution by type."""
        fig = self.theme.create_figure(figsize=(5, 4))
        ax = fig.add_subplot(111)
        
        if not data or all(d.get('stock_value', 0) == 0 for d in data):
            ax.text(0.5, 0.5, 'No inventory data', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
            ax.axis('off')
        else:
            df = pd.DataFrame(data)
            df = df[df['stock_value'] > 0].sort_values('stock_value', ascending=False)
            
            labels = df['product_type'].values[:6] if 'product_type' in df.columns else df['brand_name'].values[:6]
            values = df['stock_value'].values[:6]
            
            colors = self.theme.PALETTE_BARS[:len(labels)]
            
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=colors, startangle=90, pctdistance=0.75,
                textprops={'color': self.theme.TEXT_PRIMARY, 'fontsize': 9},
                wedgeprops=dict(width=0.4, edgecolor=self.theme.BG_CARD)
            )
            
            # Center text
            total = sum(values)
            ax.text(0, 0, f'₹{total:,.0f}\nTotal', ha='center', va='center',
                    fontsize=11, fontweight='bold', color=self.theme.TEXT_PRIMARY)
            
            ax.set_title(title, fontsize=14, fontweight='600', 
                        color=self.theme.TEXT_PRIMARY, pad=10)
        
        fig.tight_layout()
        return FigureCanvas(fig)
    
    def build_stock_status_bars(self, kpis: Dict, title: str = "Stock Status") -> FigureCanvas:
        """Build horizontal bar chart for stock status counts."""
        fig = self.theme.create_figure(figsize=(5, 3))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title)
        
        categories = ['OK', 'Low Stock', 'Out of Stock', 'Expired']
        counts = [
            kpis.get('total_variants', 0) - kpis.get('low_stock_count', 0) - 
            kpis.get('out_of_stock_count', 0) - kpis.get('expired_count', 0),
            kpis.get('low_stock_count', 0),
            kpis.get('out_of_stock_count', 0),
            kpis.get('expired_count', 0)
        ]
        colors = [self.theme.SUCCESS, self.theme.WARNING, self.theme.DANGER, '#64748B']
        
        bars = ax.barh(categories, counts, color=colors, height=0.6)
        
        for bar in bars:
            width = bar.get_width()
            if width > 0:
                ax.text(width + max(counts) * 0.02, bar.get_y() + bar.get_height()/2,
                        f'{int(width)}', va='center', fontsize=10,
                        color=self.theme.TEXT_PRIMARY, fontweight='bold')
        
        fig.tight_layout()
        return FigureCanvas(fig)
    
    # =========================================================================
    # PROFITABILITY CHARTS
    # =========================================================================
    
    def build_profit_by_product(self, data: List[Dict], title: str = "Profit by Product") -> FigureCanvas:
        """Build horizontal bar chart for profit by product."""
        fig = self.theme.create_figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, xlabel='Profit (₹)')
        
        if not data:
            ax.text(0.5, 0.5, 'No profit data', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            # Truncate names
            names = [p['product_name'][:18] + '..' if len(p['product_name']) > 18 else p['product_name'] for p in data[:8]]
            profits = [p['profit'] for p in data[:8]]
            
            colors = [self.theme.SUCCESS if p > 0 else self.theme.DANGER for p in profits]
            bars = ax.barh(names[::-1], profits[::-1], color=colors[::-1], height=0.6)
            
            # Zero line
            ax.axvline(x=0, color=self.theme.BORDER_COLOR, linewidth=1)
            
            # Value labels
            max_val = max(abs(p) for p in profits) if profits else 1
            for bar in bars:
                width = bar.get_width()
                xpos = width + max_val * 0.02 if width >= 0 else width - max_val * 0.02
                ha = 'left' if width >= 0 else 'right'
                ax.text(xpos, bar.get_y() + bar.get_height()/2,
                        f'₹{width:,.0f}', va='center', ha=ha,
                        fontsize=8, color=self.theme.TEXT_PRIMARY, fontweight='bold')
        
        fig.tight_layout()
        return FigureCanvas(fig)
    
    def build_profit_by_category(self, data: List[Dict], title: str = "Profit by Category") -> FigureCanvas:
        """Build bar chart for profit by category."""
        fig = self.theme.create_figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, ylabel='Profit (₹)')
        
        if not data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            df = pd.DataFrame(data).sort_values('profit', ascending=False)
            
            categories = df['product_type'].values[:8]
            profits = df['profit'].values[:8]
            margins = df['margin_percent'].values[:8]
            
            x = np.arange(len(categories))
            colors = [self.theme.SUCCESS if p > 0 else self.theme.DANGER for p in profits]
            bars = ax.bar(x, profits, color=colors, width=0.6, edgecolor='none')
            
            ax.set_xticks(x)
            ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=9)
            ax.axhline(y=0, color=self.theme.BORDER_COLOR, linewidth=1)
            
            # Margin labels on top
            for i, (bar, margin) in enumerate(zip(bars, margins)):
                height = bar.get_height()
                ypos = height + max(abs(p) for p in profits) * 0.02 if height >= 0 else height - max(abs(p) for p in profits) * 0.02
                va = 'bottom' if height >= 0 else 'top'
                ax.text(bar.get_x() + bar.get_width()/2, ypos,
                        f'{margin:.1f}%', ha='center', va=va,
                        fontsize=8, color=self.theme.TEXT_SECONDARY)
        
        fig.tight_layout()
        return FigureCanvas(fig)
    
    def build_margin_gauge(self, margin_percent: float, title: str = "Gross Margin") -> FigureCanvas:
        """Build a simple gauge-style chart for margin percentage."""
        fig = self.theme.create_figure(figsize=(4, 3))
        ax = fig.add_subplot(111, projection='polar')
        
        # Configure gauge
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_thetamin(0)
        ax.set_thetamax(180)
        
        # Background arc
        theta = np.linspace(0, np.pi, 100)
        ax.fill_between(theta, 0, 1, color=self.theme.GRID_COLOR, alpha=0.3)
        
        # Value arc
        value_theta = np.linspace(0, np.pi * (margin_percent / 100), 100)
        color = self.theme.SUCCESS if margin_percent >= 20 else self.theme.WARNING if margin_percent >= 10 else self.theme.DANGER
        ax.fill_between(value_theta, 0, 1, color=color, alpha=0.8)
        
        # Hide polar elements
        ax.set_rticks([])
        ax.set_thetagrids([])
        ax.spines['polar'].set_visible(False)
        
        # Center text
        ax.text(np.pi/2, -0.3, f'{margin_percent:.1f}%', ha='center', va='center',
                fontsize=24, fontweight='bold', color=self.theme.TEXT_PRIMARY,
                transform=ax.transData)
        ax.text(np.pi/2, -0.6, title, ha='center', va='center',
                fontsize=11, color=self.theme.TEXT_SECONDARY)
        
        fig.patch.set_facecolor(self.theme.BG_CARD)
        fig.tight_layout()
        return FigureCanvas(fig)
    
    # =========================================================================
    # SUPPLIER CHARTS
    # =========================================================================
    
    def build_supplier_performance(self, data: List[Dict], title: str = "Supplier Performance") -> FigureCanvas:
        """Build bar chart for supplier performance."""
        fig = self.theme.create_figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, xlabel='Products Supplied')
        
        if not data:
            ax.text(0.5, 0.5, 'No supplier data', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            names = [s['supplier_name'][:15] for s in data[:8]]
            counts = [s['product_count'] for s in data[:8]]
            
            colors = self.theme.PALETTE_BARS[:len(names)]
            bars = ax.barh(names[::-1], counts[::-1], color=colors[::-1], height=0.6)
            
            for bar in bars:
                width = bar.get_width()
                ax.text(width + max(counts) * 0.02, bar.get_y() + bar.get_height()/2,
                        f'{int(width)}', va='center', fontsize=9,
                        color=self.theme.TEXT_PRIMARY, fontweight='bold')
        
        fig.tight_layout()
        return FigureCanvas(fig)
    
    def build_lead_time_chart(self, data: List[Dict], title: str = "Avg Lead Time (Days)") -> FigureCanvas:
        """Build bar chart for supplier lead times."""
        fig = self.theme.create_figure(figsize=(6, 3))
        ax = fig.add_subplot(111)
        self.theme.apply_to_axes(ax, title=title, ylabel='Days')
        
        if not data or all(d.get('avg_lead_time', 0) == 0 for d in data):
            ax.text(0.5, 0.5, 'No lead time data', ha='center', va='center',
                    transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            df = pd.DataFrame(data)
            df = df[df['avg_lead_time'] > 0].sort_values('avg_lead_time')
            
            names = df['supplier_name'].values[:8]
            lead_times = df['avg_lead_time'].values[:8]
            
            x = np.arange(len(names))
            colors = [self.theme.SUCCESS if lt <= 7 else self.theme.WARNING if lt <= 14 else self.theme.DANGER for lt in lead_times]
            bars = ax.bar(x, lead_times, color=colors, width=0.6)
            
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height,
                        f'{height:.0f}d', ha='center', va='bottom',
                        fontsize=8, color=self.theme.TEXT_PRIMARY)
        
        fig.tight_layout()
        return FigureCanvas(fig)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def build_empty_chart(self, message: str = "No data available", figsize: tuple = (6, 4)) -> FigureCanvas:
        """Build an empty chart with a message."""
        fig = self.theme.create_figure(figsize=figsize)
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.theme.BG_CARD)
        ax.text(0.5, 0.5, message, ha='center', va='center',
                transform=ax.transAxes, color=self.theme.TEXT_SECONDARY, fontsize=14)
        ax.axis('off')
        fig.tight_layout()
        return FigureCanvas(fig)
    
    def build_kpi_sparkline(self, values: List[float], color: str = None, figsize: tuple = (2, 0.5)) -> FigureCanvas:
        """Build a mini sparkline chart for KPI cards."""
        fig = self.theme.create_figure(figsize=figsize)
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.theme.BG_CARD)
        
        if not values or len(values) < 2:
            return self.build_empty_chart("", figsize)
        
        color = color or self.theme.PRIMARY
        ax.plot(values, linewidth=1.5, color=color)
        ax.fill_between(range(len(values)), values, alpha=0.1, color=color)
        
        # Remove all axes
        ax.axis('off')
        ax.margins(x=0, y=0.1)
        
        fig.tight_layout(pad=0)
        return FigureCanvas(fig)
