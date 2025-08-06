    This script downloads a MediaWiki page, converts the raw MediaWiki source to HTML,
    downloads all images referenced in the page and saves everything to a specified folder

    Prerequisites: 
    1. You need to have Pandoc installed and available in your PATH.
       Pandoc can be downloaded from https://pandoc.org/installing.html.

    2. You need to have the Selenium WebDriver for Edge downloaded and placed in the same directory as this script. (Or similar for Chrome.)
       The WebDriver can be downloaded from https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/.
       You need to ensure that the version of the WebDriver matches your installed version of Microsoft Edge.
