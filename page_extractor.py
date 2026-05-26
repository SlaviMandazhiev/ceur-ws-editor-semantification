import requests
from bs4 import BeautifulSoup

class Extractor:

    volume = 0
    url = ""
    response = None
    html = ""

    def __init__(self, volume: int):
        self.volume = volume     
        self.url = f"https://ceur-ws.org/Vol-{self.volume}/"
        self.response = requests.get(self.url)
        if self.response.status_code == 200:
            self.html = self.response.text
        else:
            print("Web page extraction failed")
            
        
    def get_html_text(self) -> str:
        """
        Extracts the entire text of the html page
        """
        soup = BeautifulSoup(self.html, "html.parser")
        text = soup.get_text(separator="", strip=False)  
        return text
    
    def get_short_html_text(self) -> str:
        """
        Extracts and returns the raw text between the first two <hr> tags in self.html,
        preserving all original spaces, line breaks, and formatting.
        """
        soup = BeautifulSoup(self.html, "html.parser")
        start = soup.find("hr")
        if not start:
            return ""
        end = start.find_next("hr")

        # Collect raw HTML of each sibling node between the two <hr> tags
        collected = []
        for node in start.next_siblings:
            if node is end:
                break
            collected.append(str(node))

        # Re-parse the collected HTML to extract text without collapsing whitespace
        collected_html = "".join(collected)
        snippet_soup = BeautifulSoup(collected_html, "html.parser")
        text = snippet_soup.get_text(separator="", strip=False)

        return text

