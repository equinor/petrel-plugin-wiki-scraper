#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time, os, sys, subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# This script downloads a MediaWiki page, converts the raw MediaWiki source to HTML,
# downloads all images referenced in the page, and post-processes the converted HTML.
# 
# Prerequisites: 
#   1. You need to have Pandoc installed and available in your PATH.
#      Pandoc can be downloaded from https://pandoc.org/installing.html.
# 
#   2. You need to have the Selenium WebDriver for Chrome downloaded and placed in your $PATH
#      This webdriver is probably best installed using Homebrew, then:
#           xattr -d /opt/homebrew/bin/chromedriver
# 
# Creating a list of titles:
#   1. Use https://wiki.equinor.com/wiki/Special:Export to export a category to a XML file
#   2. Extract the titles
#         CAT=Software
#         sed -n  's: *<title>\(.*\)</title>:\1:p' ../*${CAT}* | egrep -v 'User:|Category:|Template:' > ${CAT}-titles.txt
#
# Download the files. Titles with an existing raw format mediawiki file are skipped. You will need to delete
# those in case you want to re-download
#   wikiscraper-macos.py ${CAT}-titles.txt # Federated logins can be a bit timing sensitive
# 
# Steps in the script:
#   1. Creates a download directory for the given title under your current directory 
#   2. Uses Selenium WebDriver to fetch the raw MediaWiki source and the rendered HTML 
#      (makes it possible to re-use credentials)
#   3. Parses the HTML to find and download all images using the browser.
#   4. Retrieves the mediawiki raw format
#   5. Converts the MediaWiki source to HTML using Pandoc.
#   6. Post-processes the HTML with BeautifulSoup to ensure <html>, <head>, and <body> tags exist,
#      adds Equinor font styles, inserts a documentation header, and removes all image captions.
# 
# Args:
#     title (str) The MediaWiki pages titles, or a filename containing the desired titles (one per line)

def sane_filename(name):
    name = name.strip()
    name = name.replace(":", "-")
    name = name.replace("/", "-")
    name = name.replace(" ", "_")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace("'", "")
    name = name.replace('"', "")
    return name

def driver():

    homedir = os.getenv('HOME')
    user_data_dir = os.path.join(homedir, "Library/Application Support/Google/Chrome")
    user_profile  = 'Default'

    # Path to your Edge WebDriver
    # For debugging: service = webdriver.ChromeService(service_args=['--log-level=DEBUG'], log_output=subprocess.STDOUT)
    service = webdriver.ChromeService()

    # Setup options
    chrome_options = Options()
    #chrome_options.add_argument("--maximized")  # Run maximized in order to prevent downscaling of images
    #chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={user_profile}")
    chrome_options.add_argument('--remote-allow-origins=*')

    # Start Edge browser
    driver = webdriver.Chrome(options=chrome_options, service=service)
    return driver


def download_page(driver, title):

    # Define the target root directory for converted wiki pages
    target_root_dir = "."  

    # Create directory for dowloaded files
    basename = sane_filename(f"{title}")
    download_dir = os.path.join(target_root_dir, basename)
    os.makedirs(download_dir, exist_ok=True)

    converted_html_file = os.path.join(download_dir, f"{basename}.html")
    markdown_file = os.path.join(download_dir, f"{basename}.md")
    mediawiki_output_file = os.path.join(download_dir, f"{basename}.mwk")
    print(f"{title} ...")
    if os.path.exists(mediawiki_output_file):
        print(f"    {title} already exists (delete {mediawiki_output_file} to reprocess)")
        return

    # Construct the wiki page URL and fetch the page source
    page_url = f"https://wiki.equinor.com/wiki/{title}"
    print(f"    Page URL {page_url}")
    print(f"    Raw wiki in {mediawiki_output_file}")
    driver.get(page_url)
    html = driver.page_source

    # Parse HTML and extract image URLs
    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")
    img_urls = [
        urljoin(page_url, img['src'])
        for img in img_tags
        if img.get('src') and img['src'].lower().endswith(('.png', '.jpg', '.gif'))
    ]

    # Remove "poweredby_mediawiki" img_url
    img_urls = [url for url in img_urls if "poweredby_mediawiki" not in url]
    
    # Download and save images using WebDriver
    for img_url in img_urls:
        try:
            driver.get(img_url)
            time.sleep(1)  # Wait for image to load

            # Get image content from browser
            img_data = driver.find_element("tag name", "img").screenshot_as_png
            img_name = os.path.basename(urlparse(img_url).path)
            #truncate anything before "px-" in the image name
            if "px-" in img_name:
                img_name = img_name.split("px-")[-1]
            img_path = os.path.join(download_dir, img_name)

            with open(img_path, "wb") as img_file:
                img_file.write(img_data)
            print(f"    Downloaded image: {img_name}")
        except Exception as e:
            print(f"    Failed to download {img_url}: {e}")


    # Download the page as MediaWiki
    mediawiki_url = f"https://wiki.equinor.com/wiki/index.php?title={title}&action=raw"
    driver.get(mediawiki_url)

    # Save MediaWiki page source
    raw_content = driver.find_element("tag name", "pre").text
    with open(mediawiki_output_file, "w", encoding="utf-8") as f:
        f.write(raw_content)

    # Use installed PanDoc to convert the MediaWiki file...
    pandoc_command = f"pandoc -f mediawiki -t markdown -o {markdown_file} {mediawiki_output_file}"
    os.system(pandoc_command)   

    #return # return here if you do not need a HTML file ...

    pandoc_command = f"pandoc -f mediawiki -t html -o {converted_html_file} {mediawiki_output_file}"
    os.system(pandoc_command)   

    if os.path.exists(converted_html_file):
        print(f"    Converted to {converted_html_file}")
    else:
        print(f"    FAILED: HTML conversion: {pandoc_command}")
        return

    # Post-process the converted HTML to ensure <html>, <head>, and <body> tags exist, and add style/header
    with open(converted_html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Ensure <html> tag exists
    if not soup.html:
        new_html = soup.new_tag("html")
        # Move all existing content into <body>
        if not soup.body:
            new_body = soup.new_tag("body")
            for elem in list(soup.contents):
                new_body.append(elem.extract())
            new_html.append(new_body)
        else:
            new_html.append(soup.body)
        soup = BeautifulSoup(str(new_html), "html.parser")

    # Ensure <head> tag exists
    if not soup.head:
        head_tag = soup.new_tag("head")
        if soup.html:
            soup.html.insert(0, head_tag)
        else:
            soup.insert(0, head_tag)

    # Ensure <body> tag exists
    if not soup.body:
        body_tag = soup.new_tag("body")
        # Move all content except <head> into <body>
        for elem in list(soup.html.contents):
            if elem.name != "head":
                body_tag.append(elem.extract())
        soup.html.append(body_tag)

    # Add stylesheet and style to <head>
    style_link = soup.new_tag("link", rel="stylesheet", href="https://cdn.eds.equinor.com/font/equinor-font.css")
    style_tag = soup.new_tag("style")
    style_tag.string = "body { font-family: 'Equinor', Arial, sans-serif; }"
    soup.head.insert(0, style_tag)
    soup.head.insert(0, style_link)

    # Add a new header at the top of <body>
    header_tag = soup.new_tag("h1")
    header_tag.string = f"Equinor Internal Plugin Documentation: {title.replace('_', ' ')}"
    soup.body.insert(0, header_tag)

    # Remove all image captions (<figcaption> tags) from the soup
    for figcaption in soup.find_all("figcaption"):
        figcaption.decompose()

    with open(converted_html_file, "w", encoding="utf-8") as f:
        f.write(str(soup))

    #delete the MediaWiki file
    #if os.path.exists(mediawiki_output_file):
    #    os.remove(mediawiki_output_file)
    #    print(f"Deleted MediaWiki file: {mediawiki_output_file}")   
        

#for title in wiki_titles:
#    download_wiki_page(title)

drv = driver()

if os.path.exists(sys.argv[1]):
    # Assume filename of titles - one per line
    with open(sys.argv[1]) as file:
        for l in file:
            download_page(drv,l.strip())
else:
    for arg in sys.argv[1::] :
        download_page(drv, arg)

drv.quit()
