import asyncio
from playwright.async_api import async_playwright
import os

async def screenshot_template(template_path, output_path):
    """Screenshot an HTML template"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Set viewport to exactly 1080x1920
        await page.set_viewport_size({"width": 1080, "height": 1920})
        
        # Load the HTML file
        file_url = f"file://{os.path.abspath(template_path)}"
        await page.goto(file_url)
        
        # Override the scaling to ensure exact 1080x1920 output
        await page.add_style_tag(content="""
            #story-card {
                transform: none !important;
                width: 1080px !important;
                height: 1920px !important;
            }
        """)
        
        # Wait for page to load completely
        await page.wait_for_load_state('networkidle')
        
        # Wait for the story-card element to be visible
        await page.wait_for_selector('#story-card')
        
        # Take screenshot of just the story-card element
        element = await page.query_selector('#story-card')
        await element.screenshot(path=output_path)
        
        await browser.close()

async def main():
    template_dir = 'templates'
    output_dir = 'screenshots'
    os.makedirs(output_dir, exist_ok=True)
    
    templates = ['cover.html', 'assaults.html', 'auto-theft.html', 'break-enter.html']
    
    for template in templates:
        template_path = os.path.join(template_dir, template)
        output_path = os.path.join(output_dir, template.replace('.html', '.png'))
        
        print(f"Screenshotting {template}...")
        await screenshot_template(template_path, output_path)
        print(f"Saved to {output_path}")

if __name__ == '__main__':
    asyncio.run(main())