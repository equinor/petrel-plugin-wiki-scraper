
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import time
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def download_wiki_page(title, output_file):
    # You need to log into the Wiki with Edge browser first
 
    # Setup Edge options
    edge_options = Options()
    edge_options.add_argument("--start-maximized")

    # Path to your Edge WebDriver
    service = Service("./msedgedriver.exe")  # Adjust path if needed

    # Start Edge browser
    driver = webdriver.Edge(service=service, options=edge_options)

    # Log in
    # page_url = f"https://wiki.equinor.com/"
 

    # Construct the wiki page URL
    page_url = f"https://wiki.equinor.com/wiki/Software:Petrel_Plugins:{title.replace(' ', '%20')}"
    driver.get(page_url)

    # Save page source
    html = driver.page_source
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Page saved to {output_file}")


    # Parse HTML and extract image URLs
    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")
    img_urls = [
        urljoin(page_url, img['src'])
        for img in img_tags
        if img.get('src') and img['src'].lower().endswith(('.png', '.jpg', '.gif'))
    ]

    # Create directory for images
    image_dir = "downloaded_images"
    os.makedirs(image_dir, exist_ok=True)

 
    # Download images using WebDriver
    for img_url in img_urls:
        try:
            driver.get(img_url)
            time.sleep(2)  # Wait for image to load

            # Get image content from browser
            img_data = driver.find_element("tag name", "img").screenshot_as_png
            img_name = os.path.basename(urlparse(img_url).path)
            img_path = os.path.join(image_dir, img_name)

            with open(img_path, "wb") as img_file:
                img_file.write(img_data)
            print(f"Downloaded image: {img_name}")
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")


    driver.quit()

# Example usage
download_wiki_page("Anonymizer", "Anonymizer.html")
