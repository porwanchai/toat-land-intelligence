import logging
from weasyprint import HTML, CSS
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ReportGeneratorService:
    @staticmethod
    def generate_pdf_report(
        plot_data: Dict[str, Any],
        audit_results: Dict[str, Any],
        calc_results: Dict[str, Any],
        setback_results: Dict[str, Any],
        ai_report: Dict[str, Any]
    ) -> bytes:
        """
        Creates elegant production-ready PDF reports compiling spatial, regulatory, and AI analysis.
        Uses WeasyPrint to transform rich HTML/CSS designs into print layouts with Thai Noto fonts support.
        """
        
        # 1. Map zones list
        zones_rows = ""
        for zone in audit_results.get("intersecting_zones", []):
            zones_rows += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;"><span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:{zone['zoning_color_code']}; margin-right:6px;"></span>{zone['zoning_color_code']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{zone['zone_type_name']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{zone['far_limit'] or 'N/A'}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{zone['osr_limit'] or 'N/A'}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{zone['coverage_percentage']:.1f}%</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{zone['intersection_area_sqm']:.1f} ตร.ม.</td>
            </tr>
            """

        # 2. Build HTML Template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: A4;
                    margin: 20mm;
                    @bottom-right {{
                        content: counter(page);
                        font-family: 'Noto Sans Thai', 'Helvetica', sans-serif;
                        font-size: 9pt;
                        color: #777;
                    }}
                }}
                body {{
                    font-family: 'Noto Sans Thai', 'Helvetica Neue', 'Helvetica', sans-serif;
                    color: #333;
                    line-height: 1.5;
                    font-size: 10pt;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px double #333;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                .header h1 {{
                    font-size: 20pt;
                    margin: 0;
                    color: #2c3e50;
                }}
                .header p {{
                    font-size: 10pt;
                    margin: 5px 0 0 0;
                    color: #7f8c8d;
                }}
                .section {{
                    margin-bottom: 25px;
                }}
                .section h2 {{
                    font-size: 14pt;
                    color: #2c3e50;
                    border-left: 4px solid #3498db;
                    padding-left: 8px;
                    margin-top: 0;
                    margin-bottom: 12px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }}
                th {{
                    background-color: #f2f2f2;
                    text-align: left;
                    font-weight: bold;
                }}
                .card {{
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                .highlight {{
                    font-weight: bold;
                    color: #2980b9;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    font-size: 8pt;
                    font-weight: bold;
                    border-radius: 4px;
                    color: white;
                    text-transform: uppercase;
                }}
                .badge-low {{ background-color: #2ecc71; }}
                .badge-medium {{ background-color: #f1c40f; }}
                .badge-high {{ background-color: #e67e22; }}
                .badge-critical {{ background-color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>รายงานการตรวจสอบผังเมืองและวิเคราะห์ศักยภาพที่ดิน</h1>
                <p>TOAT Land Intelligence & Spatial Analysis System | รายงานอย่างเป็นทางการ</p>
            </div>

            <div class="section">
                <h2>1. ข้อมูลสังเขปของที่ดิน (Plot Metadata)</h2>
                <table style="width: 100%; border: 1px solid #ddd;">
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; width: 30%;">ชื่อแปลงที่ดิน:</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{plot_data.get('plot_name') or 'ไม่ระบุ'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">ขนาดพื้นที่ทั้งหมด:</td>
                        <td style="padding: 8px; border: 1px solid #ddd;"><span class="highlight">{plot_data.get('total_area_sqm'):,.2f} ตร.ม.</span> (ประมาณ {plot_data.get('total_area_sqm', 0.0)/4.0:,.2f} ตารางวา)</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">ที่ตั้ง / ที่อยู่:</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{plot_data.get('address_text') or 'ไม่ระบุ'}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>2. ข้อมูลผังเมืองที่ครอบคลุมแปลงที่ดิน (Spatial Intersections)</h2>
                <table style="width: 100%; border: 1px solid #ddd;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="border: 1px solid #ddd; padding: 8px;">ผังสี (Color Code)</th>
                            <th style="border: 1px solid #ddd; padding: 8px;">ประเภทการใช้ประโยชน์ที่ดิน</th>
                            <th style="border: 1px solid #ddd; padding: 8px;">FAR</th>
                            <th style="border: 1px solid #ddd; padding: 8px;">OSR</th>
                            <th style="border: 1px solid #ddd; padding: 8px;">สัดส่วนคลุมดิน (%)</th>
                            <th style="border: 1px solid #ddd; padding: 8px;">พื้นที่ตัดผ่าน</th>
                        </tr>
                    </thead>
                    <tbody>
                        {zones_rows}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>3. การประเมินขีดความสามารถการก่อสร้างสูงสุด (Development Capacity)</h2>
                <div class="card">
                    <p>• พื้นที่อาคารรวมสูงสุดที่อนุญาต (Max Allowable GFA): <span class="highlight">{calc_results.get('max_gross_floor_area_sqm'):,.2f} ตร.ม.</span></p>
                    <p>• พื้นที่ว่างเพื่อการระบายน้ำ/จัดสวนตามกฎหมาย (Min Open Space Area): <span>{calc_results.get('min_open_space_area_sqm'):,.2f} ตร.ม.</span></p>
                    <p>• พื้นที่คลุมดินฐานรากอาคารสูงสุด (Max Footprint Allowed): <span>{calc_results.get('max_building_footprint_sqm'):,.2f} ตร.ม.</span></p>
                    <p>• อัตราส่วนคลุมอาคารสูงสุด (Max BCR): <span>{calc_results.get('building_coverage_ratio_percentage')}%</span></p>
                    <p>• จำนวนชั้นสูงสุดโดยประมาณ: <span class="highlight">{calc_results.get('estimated_maximum_stories')} ชั้น</span></p>
                </div>
            </div>

            <div class="section" style="page-break-before: always;">
                <h2>4. การประเมินระยะถอยร่นการก่อสร้าง (Construction Setbacks)</h2>
                <div class="card">
                    <p>• ความกว้างของถนนสาธารณะข้างแปลงที่ดิน: <span>{setback_results.get('road_width_m')} เมตร</span></p>
                    <p>• ระยะถอยร่นจากกึ่งกลาง/ขอบถนนสาธารณะตามกฎหมาย: <span>{setback_results.get('required_road_setback_m')} เมตร</span></p>
                    <p>• ระยะร่นจากแนวเขตที่ดินข้างเคียง: <span>{setback_results.get('required_property_boundary_setback_m')} เมตร</span></p>
                    <p style="font-weight: bold;">• พื้นที่จริงหลังหักระยะถอยร่นแล้ว (Buildable Envelope): <span style="color:#d35400;">{setback_results.get('buildable_envelope_area_sqm'):,.2f} ตร.ม.</span> (คิดเป็นสัดส่วน {setback_results.get('buildable_envelope_area_sqm', 0.0) * 100.0 / plot_data.get('total_area_sqm', 1.0):.1f}% ของพื้นที่แปลงทั้งหมด)</p>
                </div>
            </div>

            <div class="section">
                <h2>5. บทวิเคราะห์และความเสี่ยงโดย AI (Google Gemini Insights)</h2>
                <div class="card" style="border-left: 4px solid #2ecc71;">
                    <p><strong>ผลการประเมินศักยภาพโดยสังเขป (Executive Summary):</strong><br>{ai_report.get('executive_summary')}</p>
                    <p><strong>คะแนนประเมินความเป็นไปได้ในการลงทุน:</strong> <span class="highlight">{ai_report.get('feasibility_score')}/100</span> | ระดับความเสี่ยงทางกฎหมาย: <span class="badge badge-{ai_report.get('risk_level').lower()}">{ai_report.get('risk_level')}</span></p>
                    <p><strong>ประเภทการใช้ประโยชน์ที่ดินแนะนำ:</strong> {", ".join(ai_report.get('recommended_development_types', []))}</p>
                    <p><strong>ข้อจำกัดและข้อแนะนำทางกฎหมายควบคุมอาคาร:</strong></p>
                    <ul>
                        {"".join(f"<li>{item}</li>" for item in ai_report.get('construction_constraints', []))}
                    </ul>
                    <p><strong>หมายเหตุและเกร็ดกฎหมายเพิ่มเติม:</strong><br><span style="font-size:9pt; color:#555;">{ai_report.get('thai_regulation_notes')}</span></p>
                </div>
            </div>
        </body>
        </html>
        """

        # Compile PDF via WeasyPrint
        # Use inline CSS structure
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
