import io
import tempfile
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

def generate_dashboard_pdf(state, chart_specs, kpi_groups, kpi_data):
    """
    chart_specs: list of tuples (name, fig_factory)
                 where fig_factory is a callable returning a plotly.graph_objects.Figure
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        images = []
        for name, fig_fn in chart_specs:
            try:
                fig = fig_fn()
                image_path = f"{tmpdir}/{name.replace(' ', '_')}.png"
                fig.write_image(image_path, width=1000, height=600, scale=2)
                images.append((name, image_path))
            except Exception as e:
                print(f"[PDF Export] Failed to render {name}: {e}")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        elements = []

        start = kpi_data.get("Start date", "N/A")
        end = kpi_data.get("End date", "N/A")

        elements.append(Paragraph("<b>Market Simulation Dashboard Report</b>", styles['Title']))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(f"Simulation Period: {start} → {end}", styles['Normal']))
        elements.append(Paragraph(f"Filtered Range: {state.date_range[0]:%Y-%m-%d} → {state.date_range[1]:%Y-%m-%d}", styles['Normal']))
        elements.append(Paragraph(f"Symbols: {', '.join(state.symbols)}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

        kpi_rows = []
        for group_name, labels in kpi_groups.items():
            kpi_rows.append([Paragraph(f"<b>{group_name}</b>", styles['Heading4']), ""])
            for label in labels:
                val = kpi_data.get(label, "N/A")
                kpi_rows.append([label, val])

        kpi_table = Table(kpi_rows, hAlign='LEFT')
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#CCCCCC'),
            ('GRID', (0, 0), (-1, -1), 0.5, 'black'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 0.4 * inch))

        for name, path in images:
            elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3']))
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Image(path, width=10.5 * inch, height=6.5 * inch))
            elements.append(PageBreak())

        doc.build(elements)
        buffer.seek(0)
        return buffer