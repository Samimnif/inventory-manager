import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
#pip install lxml

def get_product_price(url):
    try:
        # Send an HTTP GET request to the URL
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the HTML content of the page
            soup = BeautifulSoup(response.text, 'html.parser')
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            print(domain)
            #print(soup.body.prettify())
            #print(soup)

            if domain == 'www.memoryexpress.com':
                price_element = soup.find('div', {'class': 'GrandTotal'})
                price_element = price_element.div
            elif domain == 'www.canadacomputers.com':
                price_element = soup.find('span', {'class': 'h2-big'})
            elif domain == 'www.amazon.ca':
                HEADERS = ({'User-Agent':
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
                'Accept-Language': 'en-US, en;q=0.5'})
                webpage = requests.get(url, headers=HEADERS)
                newsoup = BeautifulSoup(webpage.content, "lxml")
                price_element = newsoup.find('span', {'class': 'a-offscreen'})
            elif domain == 'www.dell.com':
                price_element = soup.find('div', {'class': 'ps-dell-price'})
                print(price_element)
            elif domain == "www.apple.com":
                price_element = soup.find('div', {'class': 'rc-price'})

            if price_element:
                # Extract the price text
                price = price_element.text.strip()
                return price
            else:
                return "Price not found on the page."

        else:
            return f"Failed to retrieve the page. Status code: {response.status_code}"

    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == "__main__":
    product_url = input("Enter the URL of the product page: ")
    price = get_product_price(product_url)
    print(f"Product Price: {price}")
