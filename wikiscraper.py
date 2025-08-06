
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import time
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def download_wiki_page(title):
    """
    This script downloads a MediaWiki page, converts the raw MediaWiki source to HTML,
    downloads all images referenced in the page, and post-processes the converted HTML.

    Prerequisites: 
    1. You need to have Pandoc installed and available in your PATH.
       Pandoc can be downloaded from https://pandoc.org/installing.html.

    2. You need to have the Selenium WebDriver for Edge downloaded and placed in the same directory as this script.
       The WebDriver can be downloaded from https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/.
       You need to ensure that the version of the WebDriver matches your installed version of Microsoft Edge.

    Steps in the script:
    1. Creates a download directory for the given title.
    2. Uses Selenium Edge WebDriver to fetch the raw MediaWiki source and the rendered HTML 
       (makes it possible to re-use credentials)
    3. Parses the HTML to find and download all images using the browser.
    4. Converts the MediaWiki source to HTML using Pandoc.
    5. Post-processes the HTML with BeautifulSoup to ensure <html>, <head>, and <body> tags exist,
       adds Equinor font styles, inserts a documentation header, and removes all image captions.

    Args:
        title (str): The MediaWiki page title.
    """




    # Define the target root directory for converted wiki pages
    target_root_dir = r"C:\temp\converted_wiki_pages"  
    # If all wiki pages have a common prefix, you can set it here
    # For example, if all wiki pages are under "Software:Petrel_Plugins:"
    wiki_title_prefix = "Software:Petrel_Plugins:"

    # Create directory for dowloaded files
    download_dir = os.path.join(target_root_dir, f"{title}_htlm_files")
    os.makedirs(download_dir, exist_ok=True)

    # Path to your Edge WebDriver
    service = Service("./msedgedriver.exe")  # Adjust path if needed

    # Setup Edge options
    edge_options = Options()
    edge_options.add_argument("--maximized")  # Run maximized in order to prevent downscaling of images

    # Start Edge browser
    driver = webdriver.Edge(service=service, options=edge_options)

    # Construct the wiki page URL and fetch the page source
    page_url = f"https://wiki.equinor.com/wiki/{wiki_title_prefix}{title}"
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
            print(f"Downloaded image: {img_name}")
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")


    # Download the page as MediaWiki
    mediawiki_url = f"https://wiki.equinor.com/wiki/index.php?title={wiki_title_prefix}{title}&action=raw"
    driver.get(mediawiki_url)

    #Save MediaWiki page source
    mediawiki_output_file = os.path.join(download_dir, f"{title}.mwk")
    raw_content = driver.find_element("tag name", "pre").text
    with open(mediawiki_output_file, "w", encoding="utf-8") as f:
        f.write(raw_content)

    print(f"Page saved to {mediawiki_output_file}")

    driver.quit()

    # Use installed PanDoc to convert the MediaWiki file to html
    pandoc_command = f"pandoc -f mediawiki -t html -o {os.path.join(download_dir, f'{title}.html')} {mediawiki_output_file}"
    os.system(pandoc_command)   

    # Post-process the converted HTML to ensure <html>, <head>, and <body> tags exist, and add style/header
    converted_html_file = os.path.join(download_dir, f"{title}.html")
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
    if os.path.exists(mediawiki_output_file):
        os.remove(mediawiki_output_file)
        print(f"Deleted MediaWiki file: {mediawiki_output_file}")   
        

# Process list of wiki titles (with spaces replaced by underscores)
wiki_titles_full =  ["3D_Figure",
                "Adjust_color_scale",
                "Anonymizer",
                "Attribute_Extraction",
                "Attribute_Extraction_2D",
                "Autotrack_Variance",
                "Base_of_Salt",
                "Bayesian_Dix",
                "Bayesian_VTI_correction",
                "Blend",
                "BuildAndDeploy",
                "CRS_Maps",
                "Canned_Workflows_Overview",
                "CenoBuildDbLock",
                "CenoTrack",
                "CenoUsage",
                "Ceno_Settings",
                "Cloud_Logger",
                "Color_Tables",
                "Colorgol",
                "ConversionUtil",
                "Copy_and_Paste_Colortable",
                "Cross_correlation",
                "Deli",
                "Depth_Conversion",
                "Disk_Links",
                "Export_Pointset_to_xytv-format",
                "Fault_Infill",
                "Geo-sections_with_fluids",
                "HC_Columns_Contours",
                "HC_Filled_Simple_Grid",
                "Hardware_Settings",
                "Horizon_Merger",
                "HowTo_Force_plugins_to_be_updated",
                "Import_from_Gravitas",
                "Import_of_Biostratigraphic_data",
                "Import_of_Stratigraphic_file_to_Well_Tops",
                "Import_of_stratigraphic_charts_based_on_sce-files",
                "Install_MCR",
                "Interpretation_Cleanup",
                "Interpretation_Cleanup_SIP",
                "Isochore_2D",
                "Isoproportional_Slices",
                "Max_Paleo_Temperature",
                "Mouse_Setting",
                "Multiple_Prediction",
                "Multiple_predict",
                "Naming_Convention",
                "PluginListProd",
                "PluginList_Detailed",
                "PorePressurePrediction",
                "Present_Day_Temperature",
                "QV3D",
                "RGB_Blend",
                "Regenerate_attribute_maps",
                "Rename_-_prefix_with_offset",
                "Retention_Pressure",
                "SIM_Link",
                "Score",
                "Seal_Capacity",
                "Seismic_Well_Tie",
                "Seismic_to_Pointset",
                "Setup_TEST_or_UAT_mode_of_the_Statoil_Internal_Toolbox",
                "SiteSurvey",
                "Site_Survey",
                "Sparse_Layer_Transform",
                "SpatialStacker",
                "Spatial_Stacker",
                "Statoil_Internal_Toolbox",
                "Statoil_Internal_Toolbox_Development",
                "Statoil_Tips",
                "Statoil_Top_Menu",
                "Stratigraphic_Cleanup",
                "Structural_Smoothing",
                "SubsHeat",
                "TFS2Git",
                "Temperature_Horizons",
                "Thickness_Inversion",
                "Time_Dependent_Temperature",
                "VRosion",
                "Volume_Calculation",
                "Web_Links",
                "WellDB",
                "Window_Utility"]

wiki_titles =  [] #Copy the list of titles you need from wiki_titles_full

for title in wiki_titles:
    download_wiki_page(title)

