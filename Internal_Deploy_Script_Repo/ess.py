
# or use this for Firefox:
# from selenium.webdriver.firefox.options import Options
import os
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
except ImportError:
    os.system('pip install selenium')
    os.system('pip list')



from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
def scrape_webpage(url):
    options = Options()
    # Uncomment the line below to run the browser in headless mode (no visible window)
    # options.headless = True
    driver = webdriver.Chrome(options=options)  # or webdriver.Firefox(options=options) for Firefox

    try:
        driver.get(url)

        # Here you can use Selenium methods to interact with the webpage and scrape data
        # For example, to extract all links on the page, you can do:
        links = driver.find_elements(By.TAG_NAME, 'a')
        for link in links:
            print(link.get_attribute('href'))  # Print the link URLs

        # Replace the above logic with your own to interact with the webpage and extract the specific data you need
        # You can use find_element(), find_elements(), and other Selenium methods to locate elements

    except Exception as e:
        print("Error occurred during scraping:", e)

    finally:
        driver.quit()

if __name__ == "__main__":
    # Replace this URL with the webpage you want to scrape
    target_url = "http://quotes.toscrape.com/"
    scrape_webpage(target_url)
