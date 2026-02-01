from typing import List, Dict, Any
import os
import random
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

class BusinessTools:
    """
    A collection of business-related tools for Lucy.
    Includes Shipping, Payment checking, and PDF Quote generation.
    """

    def calculate_shipping(self, destination: str, weight_kg: float) -> Dict[str, Any]:
        """
        Calculates estimated shipping cost and time.
        
        Args:
            destination (str): The destination city or country.
            weight_kg (float): Weight of the package in kilograms.
            
        Returns:
            Dict: {'cost': float, 'eta': str, 'carrier': str}
        """
        # Mock Logic
        base_rate = 15.0  # Base cost
        weight_factor = 2.5 # Cost per kg
        
        cost = base_rate + (weight_kg * weight_factor)
        
        # Random ETA
        days = random.randint(3, 7)
        eta = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        return {
            "destination": destination,
            "weight_kg": weight_kg,
            "cost_usd": round(cost, 2),
            "eta": eta,
            "carrier": "LucyExpress Logistics"
        }

    def check_payment_status(self, order_id: str) -> str:
        """
        Checks the status of a specific order.
        
        Args:
            order_id (str): The unique order identifier.
            
        Returns:
            str: The current status (PAID, PENDING, FAILED, SHIPPED).
        """
        # Mock Logic based on hash of ID to be consistent but "random"
        statuses = ["PAID", "PENDING", "SHIPPED", "FAILED", "PAID", "PAID"]
        # Use simple hash to select status
        idx = sum(ord(c) for c in order_id) % len(statuses)
        return statuses[idx]

    def generate_quote_pdf(self, items: List[Dict[str, Any]], customer_name: str) -> str:
        """
        Generates a PDF price quote for a list of items.
        
        Args:
            items (List[Dict]): List of dicts with 'name', 'qty', 'price'.
            customer_name (str): Name of the customer.
            
        Returns:
            str: Absolute path to the generated PDF.
        """
        filename = f"quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_dir = os.path.abspath("generated_docs")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Header
        elements.append(Paragraph(f"Presupuesto para: {customer_name}", styles['Title']))
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Table Data
        data = [['Producto', 'Cantidad', 'Precio Unit.', 'Total']]
        grand_total = 0.0

        for item in items:
            name = item.get('name', 'Unknown Item')
            qty = item.get('qty', 1)
            price = item.get('price', 0.0)
            total = qty * price
            grand_total += total
            data.append([name, str(qty), f"${price:.2f}", f"${total:.2f}"])

        data.append(['', '', 'TOTAL:', f"${grand_total:.2f}"])

        # Table Style
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'), # Total row bold
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Gracias por su consulta. Validez: 15 dias.", styles['Italic']))

        # Build
        doc.build(elements)
        return filepath
