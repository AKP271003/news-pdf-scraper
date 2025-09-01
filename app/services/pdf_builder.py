#!/usr/bin/env python3
import pdfkit
import os
from typing import Dict, List
from datetime import datetime
import logging
from app.config import settings

#Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFBuilder:

    def __init__(self):
        self.options = settings.PDF_OPTIONS
        self.pdf_dir = "generated_pdfs"
        os.makedirs(self.pdf_dir, exist_ok=True)

    def generate_html_content(self, articles_by_category: Dict[str, List[Dict]]) -> str:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Indian Express News Summary - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{
                    font-family: 'Times New Roman', serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }}
                .category {{
                    margin-top: 30px;
                    margin-bottom: 20px;
                }}
                .category-title {{
                    color: #d32f2f;
                    font-size: 24px;
                    font-weight: bold;
                    text-transform: uppercase;
                    border-left: 4px solid #d32f2f;
                    padding-left: 15px;
                    margin-bottom: 15px;
                }}
                .article {{
                    margin-bottom: 25px;
                    padding: 15px;
                    border: 1px solid #eee;
                    border-radius: 5px;
                }}
                .article-heading {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #1976d2;
                    margin-bottom: 10px;
                    line-height: 1.4;
                }}
                .article-summary {{
                    text-align: justify;
                    margin-bottom: 10px;
                    font-size: 14px;
                }}
                .article-link {{
                    font-size: 12px;
                    color: #666;
                    font-style: italic;
                }}
                .article-link a {{
                    color: #1976d2;
                    text-decoration: none;
                }}
                .date-generated {{
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    margin-top: 30px;
                    border-top: 1px solid #eee;
                    padding-top: 10px;
                }}
                @media print {{
                    body {{ margin: 0; }}
                    .page-break {{ page-break-before: always; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Indian Express News Summary</h1>
                <h3>{datetime.now().strftime('%B %d, %Y')}</h3>
            </div>
        """

        #Process each category
        for category, articles in articles_by_category.items():
            if not articles:
                continue

            html_content += f"""
            <div class="category">
                <div class="category-title">{category.replace('_', ' ').title()}</div>
            """

            #Add each article in the category
            for i, article in enumerate(articles):
                heading = article.get('heading', article.get('title', 'Untitled'))
                summary = article.get('summary', 'Summary not available.')
                url = article.get('url', '#')

                page_break = 'class="article page-break"' if i > 0 and i % 3 == 0 else 'class="article"'

                html_content += f"""
                <div {page_break}>
                    <div class="article-heading">{heading}</div>
                    <div class="article-summary">{summary}</div>
                    <div class="article-link">
                        <strong>Read full article:</strong> 
                        <a href="{url}">{url}</a>
                    </div>
                </div>
                """

            html_content += "</div>\n"

        #Close HTML
        html_content += f"""
            <div class="date-generated">
                Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by News PDF Scraper
            </div>
        </body>
        </html>
        """

        return html_content

    def generate_pdf(self, articles_by_category: Dict[str, List[Dict]], output_filename: str = None) -> str:
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            categories = "_".join(list(articles_by_category.keys())[:3])
            output_filename = f"news_summary_{categories}_{timestamp}.pdf"

        output_path = os.path.join(self.pdf_dir, output_filename)

        try:
            #Generate HTML content
            html_content = self.generate_html_content(articles_by_category)

            #Convert HTML to PDF
            pdfkit.from_string(
                html_content, 
                output_path, 
                options=self.options
            )

            logger.info(f"Successfully generated PDF: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise RuntimeError(f"PDF generation failed: {e}")

'''
    def generate_test_pdf(self) -> str:
        test_articles = {
            "test": [
                {
                    "heading": "Test Article Heading",
                    "summary": "This is a test summary to verify that PDF generation is working correctly. The system can scrape articles from Indian Express, summarize them with AI, and generate clean PDF reports.",
                    "url": "https://indianexpress.com/test"
                }
            ]
        }

        return self.generate_pdf(test_articles, "test_pdf_generation.pdf")
'''

pdf_builder = PDFBuilder()
