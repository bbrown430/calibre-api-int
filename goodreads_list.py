from src.scaper import Scraper
from src.book import Book
from src.io_utils import IOUtils
import validators
import math
import re

class GoodreadsList(Scraper):
    def __init__(self):
        super().__init__()
    
    def link_checker(self, list_url):
        if validators.url(list_url):
            if "/review/" in list_url:
                page = 1
                # Check if URL already has query parameters
                separator = "&" if "?" in list_url else "?"
                formatted_url = list_url + f"{separator}page={page}&per_page=10"
                return "profile", formatted_url
            elif "/list/show" in list_url:
                return "listopia", list_url
            elif "/series/" in list_url:
                return "series", list_url
        else:
            return None, False
            
    # scrapes a list of books from a goodreads list, given the list url    
    def scrape(self, list_url):
        page = 1
        
        type, url = self.link_checker(list_url)
        
        if not url:
            return None
        
        soup = IOUtils.cook_soup(url)
        
        goodreads_books = []
        if type == "profile":
            # determine number of books on shelf from title tag
            # Format: "Name's 'shelf-name' books on Goodreads (N books)"
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.text
                match = re.search(r'\((\d+)\s*books?\)', title_text)
                if match:
                    self.book_count = int(match.group(1))
                else:
                    # Fallback: count books on first page and estimate
                    self.book_count = 100  # Default estimate
            else:
                self.book_count = 100

            # get list name from title
            if title_tag:
                # Extract shelf name from title like "Brian Brown's 'want-to-read' books on Goodreads"
                title_text = title_tag.text
                match = re.search(r"'([^']+)'", title_text)
                if match:
                    self.list_name = match.group(1)
                else:
                    # Fallback for "all" shelf format
                    self.list_name = "goodreads-books"
            else:
                self.list_name = "goodreads-books"

            # Always use all books
            pages_needed = math.ceil(self.book_count / 10)

            books_remaining = self.book_count
            while page <= pages_needed and books_remaining > 0:
                book_table = soup.find("tbody", {"id": "booksBody"})
                if not book_table:
                    print("Could not find booksBody table")
                    break
                book_list = book_table.findAll("tr")
                if not book_list:
                    break
                if books_remaining < 10:
                    book_list = book_list[:books_remaining]
                for book_html in book_list:
                    goodreads_book = Book(book_html, "profile")
                    goodreads_book.set_directory(self.list_name)
                    goodreads_books.append(goodreads_book)
                books_remaining -= len(book_list)
                page += 1
                separator = "&" if "?" in list_url else "?"
                url_with_attrs = list_url + f"{separator}page={page}&per_page=10"
                soup = IOUtils.cook_soup(url_with_attrs)
        
        if type == "listopia":
            # get book count
            book_count_container = soup.find("div", class_="stacked")
            book_string = book_count_container.text.strip().split(' books')[0].strip()
            book_count_string = book_string.replace(",", "")
            self.book_count = int(book_count_string)    
            # get list title
            self.list_name = soup.find("h1", class_="gr-h1 gr-h1--serif").text.strip()                

            # Always use all books
            pages_needed = math.ceil(self.book_count / 100)

            books_remaining = self.book_count
            while page <= pages_needed and books_remaining > 0:
                book_list = soup.find_all("tr")
                if books_remaining < 100:
                    book_list = book_list[:books_remaining]
                for book_html in book_list:
                    goodreads_book = Book(book_html, "listopia")
                    goodreads_book.set_directory(self.list_name)
                    goodreads_books.append(goodreads_book)
                books_remaining -= len(book_list)
                page += 1
                url_with_attrs = list_url + f"&page={page}"
                soup = IOUtils.cook_soup(url_with_attrs)
        
        if type == "series":
            # get book count
            book_count_container = soup.find("div", class_="responsiveSeriesHeader__subtitle u-paddingBottomSmall").text
            book_count = int(book_count_container.split(" ")[0])
            
            # get list name
            raw_list_name = soup.text
            filtered_list_name = raw_list_name.replace("\n", "")
            name_split = filtered_list_name.split(" by")
            self.list_name = name_split[0]
            
            # get books
            book_list = soup.find_all("div", class_="listWithDividers__item")
            main_series_count = 0
            
            for book_html in book_list:
                if main_series_count < book_count:
                    entry_number_container = book_html.find("h3").text
                    entry_number_str = entry_number_container.split("Book ")[1]
                    # Skip entries with a dash in the number (e.g., '1-2')
                    if "-" in entry_number_str:
                        continue
                    try:
                        entry_number_float = float(entry_number_str.strip())
                    except ValueError:
                        print(f"Warning: Could not parse book number from '{entry_number_container}'. Skipping entry.")
                        continue
                    if entry_number_float % 1 == 0: #determine if main series entry
                        if entry_number_float != 0:
                            main_series_count += 1
                        goodreads_book = Book(book_html, "series")
                        goodreads_book.set_directory(self.list_name)
                        goodreads_books.append(goodreads_book)
                        
            
        
        return goodreads_books
