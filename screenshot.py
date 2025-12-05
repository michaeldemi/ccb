import asyncio
from playwright.async_api import async_playwright
import os

async def screenshot_template(template_path, output_path):
    """Screenshot an HTML template"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Set viewport to match template (1080x1920)
        await page.set_viewport_size({"width": 1080, "height": 1920})
        
        # Load the HTML file
        file_url = f"file://{os.path.abspath(template_path)}"
        await page.goto(file_url)
        
        # Wait for page to load completely
        await page.wait_for_load_state('networkidle')
        
        # Take screenshot
        await page.screenshot(path=output_path, full_page=True)
        
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