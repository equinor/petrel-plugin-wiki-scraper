
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import time
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def download_wiki_page(title):

    # Create directory for dowloaded files
    download_dir = f"{title}_htlm_files"
    os.makedirs(download_dir, exist_ok=True)

    # You need to log into the Wiki with Edge browser first
 
    # Setup Edge options
    edge_options = Options()
    edge_options.add_argument("--window-size=500,500")

    # Path to your Edge WebDriver
    service = Service("./msedgedriver.exe")  # Adjust path if needed

    # Start Edge browser
    driver = webdriver.Edge(service=service, options=edge_options)

    # Log in
    # page_url = f"https://wiki.equinor.com/"
 
    # Download the page as MediaWiki
    mediawiki_url = f"https://wiki.equinor.com/wiki/index.php?title=Software:Petrel_Plugins:{title}&action=raw"
    driver.get(mediawiki_url)

    #Save MediaWiki page source
    mediawiki_output_file = os.path.join(download_dir, f"{title}.mwk")
    raw_content = driver.find_element("tag name", "pre").text
    with open(mediawiki_output_file, "w", encoding="utf-8") as f:
        f.write(raw_content)

    print(f"Page saved to {mediawiki_output_file}")

    # Construct the wiki page URL
    page_url = f"https://wiki.equinor.com/wiki/Software:Petrel_Plugins:{title}"
    driver.get(page_url)
    #Save MediaWiki page source

    # Save page source
    html_output_file = os.path.join(download_dir, f"{title}.html")
    html = driver.page_source
    with open(html_output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Page saved to {html_output_file}")


    # Parse HTML and extract image URLs
    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")
    img_urls = [
        urljoin(page_url, img['src'])
        for img in img_tags
        if img.get('src') and img['src'].lower().endswith(('.png', '.jpg', '.gif'))
    ]

 
    # Download images using WebDriver
    for img_url in img_urls:
        try:
            driver.get(img_url)
            time.sleep(2)  # Wait for image to load

            # Get image content from browser
            img_data = driver.find_element("tag name", "img").screenshot_as_png
            img_name = os.path.basename(urlparse(img_url).path)
            img_path = os.path.join(download_dir, img_name)

            with open(img_path, "wb") as img_file:
                img_file.write(img_data)
            print(f"Downloaded image: {img_name}")
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")


    driver.quit()

    # Use installed PanDoc to convert the MediaWiki file to html
    pandoc_command = f"pandoc -f mediawiki -t html -o {os.path.join(download_dir, f'{title}_converted.html')} {mediawiki_output_file}"
    os.system(pandoc_command)   

# Example usage
wiki_titles = ["Anonymizer"]
for title in wiki_titles:
    download_wiki_page(title)

