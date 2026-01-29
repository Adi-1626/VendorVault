"""
PDF generation utilities for invoices.
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import List
import os
import config
from src.models.bill import Bill, BillItem


class PDFGenerator:
    """Generate PDF invoices."""
    
    def __init__(self):
        self.page_size = letter
        self.margin = 0.75 * inch
    
    def num_to_words(self, num):
        """Convert number to Indian currency words."""
        try:
            num = int(num)
            if num == 0: return "Zero"
            
            words = {
                0: '', 1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 
                6: 'Six', 7: 'Seven', 8: 'Eight', 9: 'Nine', 10: 'Ten', 
                11: 'Eleven', 12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen', 
                15: 'Fifteen', 16: 'Sixteen', 17: 'Seventeen', 18: 'Eighteen', 
                19: 'Nineteen', 20: 'Twenty', 30: 'Thirty', 40: 'Forty', 
                50: 'Fifty', 60: 'Sixty', 70: 'Seventy', 80: 'Eighty', 90: 'Ninety'
            }
            
            def get_words(n):
                if n < 20: return words[n]
                if n < 100: return words[n - n % 10] + (" " + words[n % 10] if n % 10 else "")
                if n < 1000: return words[n // 100] + " Hundred" + (" " + get_words(n % 100) if n % 100 else "")
                if n < 100000: return get_words(n // 1000) + " Thousand" + (" " + get_words(n % 1000) if n % 1000 else "")
                if n < 10000000: return get_words(n // 100000) + " Lakh" + (" " + get_words(n % 100000) if n % 100000 else "")
                return get_words(n // 10000000) + " Crore" + (" " + get_words(n % 10000000) if n % 10000000 else "")

            return get_words(num) + " Only"
        except:
            return ""

    def generate_invoice(self, bill: Bill, filename: str = None) -> str:
        """Generate professional Indian GST Invoice."""
        if filename is None:
            filename = f"INV_{bill.bill_no}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        output_dir = config.get_generated_bills_dir()
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        pdf = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # === HEADER ===
        # Company Details
        company_header = [
            [Paragraph("<b>JAYLAXMI FOOD PROCESSING PVT. LTD.</b>", ParagraphStyle('H1', fontSize=18, textColor=colors.HexColor('#8B4513'), alignment=1))],
            [Paragraph("<i>(Free Time - Fun Time, All The Time!)</i>", ParagraphStyle('H2', fontSize=10, textColor=colors.black, alignment=1))],
            [Paragraph("Sr.No.135/1, Dhayari, Nanded Phata, Sinhgad Road, Pune - 411 041", ParagraphStyle('Addr', fontSize=9, alignment=1))],
            [Paragraph("GSTIN: <b>27AADCJ0128Q1ZC</b>  |  CIN: U15490PN2013PTC146054  |  Mob: 8446061316", ParagraphStyle('GST', fontSize=9, alignment=1))]
        ]
        t_header = Table(company_header, colWidths=[7.5*inch])
        t_header.setStyle(TableStyle([
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.black),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 0.2*inch))
        
        # "TAX INVOICE" Title
        elements.append(Paragraph("<b>TAX INVOICE</b>", ParagraphStyle('Title', fontSize=14, alignment=1, spaceAfter=10)))
        
        # Invoice Info & Customer Info Side-by-Side
        cust_info = [
            [Paragraph(f"<b>Invoice No:</b> {bill.bill_no}", styles['Normal']), Paragraph(f"<b>Date:</b> {bill.date}", styles['Normal'])],
            [Paragraph(f"<b>Customer:</b> {bill.customer_name}", styles['Normal']), Paragraph(f"<b>Place of Supply:</b> Maharashtra (27)", styles['Normal'])],
            [Paragraph(f"<b>Phone:</b> {bill.customer_no}", styles['Normal']), Paragraph("<b>Payment Mode:</b> Cash/UPI", styles['Normal'])]
        ]
        t_info = Table(cust_info, colWidths=[4*inch, 3.5*inch])
        t_info.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 0.2*inch))
        
        # === ITEMS TABLE ===
        # Cols: Sr, Product, HSN, Qty, Rate, Taxable, CGST, SGST, Total
        headers = ['Sr', 'Product Description', 'HSN', 'Qty', 'Rate', 'Taxable', 'CGST\n(2.5%)', 'SGST\n(2.5%)', 'Total']
        data = [headers]
        
        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        total_qty = 0
        
        # Calculate items
        tax_rate = getattr(bill, 'tax_rate', 5.0) # Default 5% for food
        half_tax = tax_rate / 2
        
        for idx, item in enumerate(bill.items, 1):
            qty = item.quantity
            rate = item.unit_price # Assuming rate is taxable value per unit
            taxable = qty * rate
            cgst = taxable * (half_tax / 100)
            sgst = taxable * (half_tax / 100)
            row_total = taxable + cgst + sgst
            
            # Update totals
            total_taxable += taxable
            total_cgst += cgst
            total_sgst += sgst
            total_qty += qty
            
            row = [
                str(idx),
                Paragraph(item.product_name, ParagraphStyle('Cell', fontSize=9)),
                "1905", # Default HSN for food
                str(qty),
                f"{rate:.2f}",
                f"{taxable:.2f}",
                f"{cgst:.2f}",
                f"{sgst:.2f}",
                f"{row_total:.2f}"
            ]
            data.append(row)
            
        # Total Row
        data.append([
            '', 'Total', '', str(total_qty), '', 
            f"{total_taxable:.2f}", f"{total_cgst:.2f}", f"{total_sgst:.2f}", f"{bill.total:.2f}"
        ])
        
        # Table Style
        col_widths = [0.4*inch, 2.6*inch, 0.6*inch, 0.5*inch, 0.7*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.9*inch]
        t_items = Table(data, colWidths=col_widths, repeatRows=1)
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'), # Product left align
            ('ALIGN', (4,0), (-1,-1), 'RIGHT'), # Numbers right align
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), # Total row bold
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#E5E7EB')),
        ]))
        elements.append(t_items)
        elements.append(Spacer(1, 0.2*inch))
        
        # === SUMMARY SECTION ===
        # Amount in Words
        amt_words = self.num_to_words(bill.total)
        
        summary_data = [
            [Paragraph(f"<b>Amount in Words:</b><br/>{amt_words} Rupees Only", styles['Normal']),
             Paragraph(f"<b>Taxable Amount:</b> Rs.{total_taxable:.2f}<br/><b>Total Tax (GST):</b> Rs.{total_cgst+total_sgst:.2f}<br/><b>Grand Total:</b> Rs.{bill.total:.2f}", 
                       ParagraphStyle('TotalBlock', fontSize=10, leading=14, alignment=2))]
        ]
        t_summary = Table(summary_data, colWidths=[4.5*inch, 3*inch])
        t_summary.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('background', (1,0), (1,0), colors.HexColor('#F9FAFB'))
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 0.5*inch))
        
        # Signatories
        sig_data = [
            [Paragraph("<b>Terms & Conditions:</b><br/>1. Goods once sold will not be taken back.<br/>2. Subject to Pune Jurisdiction.", ParagraphStyle('TnC', fontSize=8)),
             Paragraph("<b>For Jaylaxmi Food Processing Pvt. Ltd.</b><br/><br/><br/><br/>Authorized Signatory", ParagraphStyle('Sig', alignment=2, fontSize=9))]
        ]
        t_sig = Table(sig_data, colWidths=[4*inch, 3.5*inch])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(t_sig)
        
        pdf.build(elements)
        return output_path
    
    def generate_simple_invoice(self, bill: Bill, filename: str = None) -> str:
        """
        Generate a simple invoice using canvas (faster, simpler layout).
        
        Args:
            bill: Bill object
            filename: Output filename (optional)
        
        Returns:
            str: Path to generated PDF file
        """
        if filename is None:
            filename = f"{bill.bill_no}.pdf"
        
        output_dir = config.get_generated_bills_dir()
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, height - 50, config.COMPANY_NAME)
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 80, "INVOICE")
        
        # Invoice details
        c.setFont("Helvetica", 11)
        y = height - 120
        c.drawString(50, y, f"Invoice No: {bill.bill_no}")
        c.drawRightString(width - 50, y, f"Date: {bill.date}")
        
        y -= 25
        c.drawString(50, y, f"Customer: {bill.customer_name}")
        c.drawRightString(width - 50, y, f"Phone: {bill.customer_no}")
        
        # Items table
        y -= 40
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Product")
        c.drawString(350, y, "Qty")
        c.drawRightString(width - 50, y, "Amount")
        
        y -= 5
        c.line(50, y, width - 50, y)
        
        c.setFont("Helvetica", 10)
        y -= 20
        
        for item in bill.items:
            c.drawString(50, y, item.product_name[:40])  # Truncate long names
            c.drawString(350, y, str(item.quantity))
            c.drawRightString(width - 50, y, f"₹{item.get_total():.2f}")
            y -= 20
            
            if y < 150:  # Avoid footer area
                break
        
        # Totals
        y -= 20
        c.line(350, y, width - 50, y)
        y -= 25
        
        c.drawRightString(width - 150, y, "Subtotal:")
        c.drawRightString(width - 50, y, f"₹{bill.subtotal:.2f}")
        
        y -= 20
        c.drawRightString(width - 150, y, "Discount:")
        c.drawRightString(width - 50, y, f"₹{bill.discount:.2f}")
        
        y -= 20
        c.drawRightString(width - 150, y, f"Tax ({bill.tax_rate}%):")
        c.drawRightString(width - 50, y, f"₹{bill.tax_amount:.2f}")
        
        y -= 10
        c.setLineWidth(2)
        c.line(350, y, width - 50, y)
        y -= 25
        
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 150, y, "Total:")
        c.drawRightString(width - 50, y, f"₹{bill.total:.2f}")
        
        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(width / 2, 30, "Thank you for your business!")
        
        c.save()
        return output_path
