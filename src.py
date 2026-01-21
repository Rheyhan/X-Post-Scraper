import pandas as pd
import json
import time
from tqdm import tqdm
from typing import *
import re
import os
from IPython.display import clear_output
import shutil
from datetime import datetime, timedelta
import warnings
import random as rd
# Scrapping and crawling modules
import undetected_chromedriver as uc
from requests.utils import quote, unquote
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


lang_codes = {'Arabic': 'ar',
            'Arabic (Feminine)': 'ar-x-fm',
            'Bangla': 'bn',
            'Basque': 'eu',
            'Bulgarian': 'bg',
            'Catalan': 'ca',
            'Croatian': 'hr',
            'Czech': 'cs',
            'Danish': 'da',
            'Dutch': 'nl',
            'English': 'en',
            'Finnish': 'fi',
            'French': 'fr',
            'German': 'de',
            'Greek': 'el',
            'Gujarati': 'gu',
            'Hebrew': 'he',
            'Hindi': 'hi',
            'Hungarian': 'hu',
            'Indonesian': 'id',
            'Italian': 'it',
            'Japanese': 'ja',
            'Kannada': 'kn',
            'Korean': 'ko',
            'Marathi': 'mr',
            'Norwegian': 'no',
            'Persian': 'fa',
            'Polish': 'pl',
            'Portuguese': 'pt',
            'Romanian': 'ro',
            'Russian': 'ru',
            'Serbian': 'sr',
            'Simplified Chinese': 'zh-cn',
            'Slovak': 'sk',
            'Spanish': 'es',
            'Swedish': 'sv',
            'Tamil': 'ta',
            'Thai': 'th',
            'Traditional Chinese': 'zh-tw',
            'Turkish': 'tr',
            'Ukrainian': 'uk',
            'Urdu': 'ur',
            'Vietnamese': 'vi'}

def getTime(str: str) -> datetime:

    '''
    Convert string of datetime in isoformat to datetime object and adjust the timezone


    Parameters
    ------------
    - str: str

        String of datetime in isoformat

    Returns
    ------------
    - date_time_obj: datetime
        Datetime object adjusted to UTC+7
    '''

    date_time_obj = datetime.fromisoformat(str)
    hour_offset = int(time.strftime("%z", time.gmtime())[:3])                 # Shit code to get ur timezone
    date_time_obj =date_time_obj + timedelta(hours=hour_offset)

    return date_time_obj


def safelyTurnStrToUnixTime(str: str) -> int:
    '''
    This function is used to safely turn a string of datetime in "YYYY-MM-DD-HH:MM:SS" format to unix timestamp

    Parameters
    ------------
    - str: str
        String of datetime in "YYYY-MM-DD-HH:MM:SS" format
    
    Returns
    ------------
    - int
        unix timestamp of the given datetime string
    '''
    dt = datetime.strptime(str, "%Y-%m-%d-%H:%M:%S")
    unix_timestamp = int(dt.timestamp())
    return unix_timestamp

def minOneDay(time: int) -> int:
    '''
    This function is used to subtract one day from the given date
    
    Parameters
    -----------
    - time: int
        unix timestamp of the date to subtract one day from

    Returns
    -----------
    - int
        unix timestamp of the date after subtracting one day
    '''
    date_time_obj = datetime.fromtimestamp(time)
    date_time_obj -= timedelta(days=1)
    date_time_obj = int(date_time_obj.timestamp())
    
    return date_time_obj

def wait(timeout: int = 10) -> None:
    '''
    just a glorified simple function to wait for a certain amount of time with a progress bar.

    Parameters
    -----------
    - timeout: int
        Time to wait in seconds
    '''
    for _ in tqdm(range(timeout), desc="Waiting"):
        time.sleep(1)
    clear_output()


def safe_int_from_aria(aria_label: str) -> int:
    '''
    Safely extract an integer from an aria-label string.

    Parameters
    ----------
    - aria_label : str
        The aria-label string containing the number.
    
    Returns
    -------
    - int
        The extracted integer from the aria-label string. Returns 0 if no integer is found.
    '''
    match = re.search(r"\d+", aria_label or "")
    return int(match.group(0)) if match else 0



class twitterScrapper:
    '''
    This class is used to scrape posts from X (formerly known as Twitter) based on given filters and date range.
    
    Methods
    ----------
    - login()
        - Logs into Twitter using the provided credentials
    - start()
        - Starts the scraping process based on the given filters and date range
    '''

    def __init__(self, credentials: str = "Credentials/twitter.json"):
        '''
        This function is used to initialize the class and will also login to twitter
        
        Parameters
        ----------
        credentials : str
            - Path to the twitter credentials json file
            - The json file should be in the following format:
            ```
            {   "username" : "your_username",
                "password" : "your_password",
                "email"    : "your_email"}
            ```
        '''
        
        # Bunch of checkers and loaders for credentials
        if not os.path.exists(credentials):
            raise FileNotFoundError("Credentials file not found!")
        with open(credentials, "r") as f:
            credentials = json.load(f)
            try:
                username = credentials["username"]
                password = credentials["password"]
                email = credentials["email"]
            except KeyError:
                raise KeyError("Credentials file is not in the correct format!")
        
        # Check if any of those credentials is None
        if username is None or password is None:
            raise ValueError("Username or password can't be empty!")
        if email is None:
            warnings.warn("Email is not provided, this shit might not work if suspicious login attempt is detected!", UserWarning)

        self.username = username
        self.password = password
        self.email = email

        # For storing all the data during scraping
        self.theDict = { "User" : [], "Date" : [], "post_text" : [], "quotedPost_text" : [],
                         "Reply_count": [], "Repost_count": [], "Like_count": [], "View_count": []}
        
        self.login()

    # Utilities for this class
    def _build_search_url(self, date_limit: str) -> str:
        '''
        Build the search URL based on the Filters and given datelimit

        Parameters
        ----------
        - date_limit : str
            The date limit for the search in the format "YYYY-MM-DD".
        
        Returns
        -------
        - str
            The constructed search URL.
        '''
        return f"{self.SEARCH_URL}{self.FILTERS_COMBINATION}{quote(f' until_time:{date_limit}')}&f=live&src=typed_query"

    def _scrape_detected(self) -> bool:
        '''
        Check if scraping is detected by looking for the "Something went wrong. Try reloading." message. 

        Returns
        -------
        - bool
            True if scraping is detected (based on the presence of the error message), False otherwise.
        '''
        
        try:
            sumthingwrong = WebDriverWait(self.driver, self.WAIT_LONG).until(
                 EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Home timeline"]/div/div/div/span'))
            )
            sumthingwrong.text == "Something went wrong. Try reloading."
            return True
        
        except TimeoutException:
            return False

    def _wait_for_posts(self, current_date: int, counter: int) -> tuple[int, int, bool]:
        '''
        Wait for posts to load on the page. If no posts are found within the timeout period, step back one day and increment the counter.

        The counter tracks the number of consecutive days with no posts found. If the counter exceeds the maximum allowed empty pages, the function indicates that all posts have been reached.

        Parameters
        ----------
        - current_date : int
            unix timestamp representing the current date being checked for posts.
        - counter : int
            The number of consecutive days with no posts found.
        
        Returns
        -------
        - tuple[int, int, bool]
            A tuple containing the updated current date, the updated counter, and a boolean indicating whether the maximum number of empty pages has been reached.
        '''

        try:
            # Is there a container for post?
            WebDriverWait(self.driver, self.WAIT_LONG).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testid='cellInnerDiv']"))
            )
            counter = 0
            return current_date, counter, False # Yes
        except TimeoutException:
            current_date = minOneDay(current_date)
            counter += 1
            current_date_str = datetime.fromtimestamp(current_date).strftime("%Y-%m-%d")
            print(f"No posts found, stepping back to {current_date_str}, attempt {counter + 1}/{self.MAX_EMPTY_PAGES}")
            return current_date, counter, counter >= self.MAX_EMPTY_PAGES    # Nothingburger and minus by one day

    def _parse_post(self, post_element) -> str:
        '''
        Parse the post element to extract the full text of the post.

        NOTE: This only handles text, links, emojis, and such. Media (images, videos, gifs) are not handled ***yet***.

        Parameters
        ----------
        - post_element : WebElement
            The WebElement representing the post.
        
        Returns
        -------
        - str
            The full text of the post.
        '''

        parts = post_element.find_elements(By.XPATH, ".//span | .//img | .//a[@dir='ltr']")
        text = ""
        for p in parts:
            if p.tag_name == "img":                 # Emojis
                text += p.get_attribute("alt")
            elif p.tag_name == "a":                 # Links (Not shortened with t.co domain)
                text += p.text + " "
            else:                                   # Normal text                 
                text += p.text
        return text

    def _extract_post_data(self, element) -> tuple[str, str, str, str]:
        '''
        Extract post data from the given post element.

        Parameters
        ----------
        - element : WebElement
            The WebElement representing the post.
        
        Returns
        ------
        - tuple[str, str, str, str]
            A tuple containing the post text, quoted post text, post user, and post date.
        '''

        # Get the entire post element
        post_element = element.find_element(
            By.XPATH, './/div[not(@role="link")]/div/div/div/div/div[@data-testid="tweetText"]',
        )
        # Post
        post_text = self._parse_post(post_element)

        # Quoted Post
        try:
            quoted_element = element.find_element(By.XPATH, './/div[@role="link"]')
            quoted_text = ''.join(
                i.text for i in quoted_element.find_elements(By.XPATH, './/div[@data-testid="tweetText"]/span')
            )
        except NoSuchElementException:
            quoted_text = ""

        post_date = getTime(element.find_element(By.XPATH, './/time').get_attribute("datetime")).strftime("%Y-%m-%d-%H:%M:%S")
        post_user = element.find_element(By.XPATH, './/a/div/span').text

        return post_text, quoted_text, post_user, post_date
    
    def _write_json(self, filename: str) -> None:
        '''
        Write the scraped data to a JSON file.
        
        Parameters
        ----------
        - filename : str
            The name of the file to write the JSON data to.
        '''
        # theDict conversion to a list of dictionaries
        theDict_JSON = {i: {
                j: self.theDict[j][i] for j in self.theDict.keys()
            } for i in range(len(self.theDict["post_text"]))
            }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(theDict_JSON, f, ensure_ascii=False, indent=4)

    def _write_csv(self, filename: str) -> None:
        '''
        Write the scraped data to a CSV file.

        Parameters
        ----------
        - filename : str
            The name of the file to write the CSV data to.
        '''
        df = pd.DataFrame(self.theDict)
        df.to_csv(filename, index=False)

    def _load_latest_savepoint(self) -> bool:
        '''
        Load the latest savepoint from the Savepoints directory.

        Uses the eariest date as the `self.start_date` from the most recently modified file in the Savepoints directory and loads the data into `self.theDict`.

        Returns
        -------
        - bool
            True if a savepoint was loaded, False otherwise.
        '''

        save_dir = f"Process/{self.processDir}/Savepoints"

        # Checkers if there's any savepoint
        if not os.path.isdir(save_dir):
            return False
        files = [f for f in os.listdir(save_dir) if f.endswith((".csv", ".json"))]
        if not files:
            return False
        
        # Get the latest savepoint file
        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(save_dir, f)))
        latest_path = os.path.join(save_dir, latest_file)

        if latest_file.endswith(".csv"):
            df = pd.read_csv(latest_path)
        else:
            with open(latest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame.from_dict(data, orient="index")
        
        self.theDict = {col: df[col].tolist() for col in df.columns}    # Convert DataFrame to dictionary
        if "Date" in self.theDict and self.theDict["Date"]:
            try:
                earliest_dt = min(
                    datetime.strptime(d, "%Y-%m-%d-%H:%M:%S")
                    for d in self.theDict["Date"]
                    if isinstance(d, str)
                )
                self.start_date = int(earliest_dt.timestamp())
            except Exception:
                pass

        print(f"Resumed from savepoint: {latest_file}")
        return True

    def save(self, type: Literal["final", "savepoint"]) -> str:
        '''
        Save the current progress to a file.

        file extension and format is based on `self.saveFormat`.

        Parameters
        ----------
        - type : Literal["final", "savepoint"]
            The type of save to perform. "final" for final save, "savepoint" for intermediate savepoint.
        
        Returns
        -------
        - str
            The path to the saved file.
        '''
        if type not in {"final", "savepoint"}:
            raise ValueError("Save type must be 'final' or 'savepoint'.")

        os.makedirs(f"Process/{self.processDir}/Savepoints", exist_ok=True)
        
        if type == "savepoint":
            save_path = f"Process/{self.processDir}/Savepoints/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        else:
            save_path = f"Process/{self.processDir}/Final"

        if self.saveFormat == "csv":
            self._write_csv(f"{save_path}.csv")
        elif self.saveFormat == "json":
            self._write_json(f"{save_path}.json")
        elif self.saveFormat == "both":
            self._write_csv(f"{save_path}.csv")
            if type == "final":                         # There's no fucking logic to save both on savepoint, only do it on final save
                self._write_json(f"{save_path}.json")
        else:
            raise ValueError("saveFormat must be 'csv', 'json', or 'both'.")
        
        return save_path    # This ain't used, but yeah.
    
    def login(self) -> None:
        '''
        Tries to login to the account based from the given credentials

        Will use `self.username` and `self.password` only. However, if X detects your login as suspicious, `self.email` will be used.

        Raises
        ------
        - ValueError
            If email is required due to suspicious login attempt, but email is not provided on credentials.
        '''
        # Initialize the driver and check bot detection
        self.driver = uc.Chrome()
        self.driver.get('https://www.browserscan.net/bot-detection')

        # Check bot detection, 
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, '//div[@class="_oxrqr1"]')))
        time.sleep(4)
        botResult = self.driver.find_element(By.XPATH, '//strong[@class="_1ikblmd"]').text
        if botResult != "Normal":
            warnings.warn("Bot detection failed! X login might be detected as bot", UserWarning)

        # Get to X login page
        self.driver.get("https://x.com/i/flow/login")
        time.sleep(5)

        # Login handling
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//input[@autocomplete = 'username']")))
        time.sleep(3)
        username_input = self.driver.find_element(By.XPATH, "//input[@autocomplete = 'username']")
        for i in self.username:
            username_input.send_keys(i)
            time.sleep(rd.uniform(0.05, 0.2))
        self.driver.find_element(By.XPATH, "//div/button[2]").click()
        time.sleep(5)

        # if email is needed. This means you logged a lot to the account and X raises a suspicious login attempt.
        try:
            if self.driver.find_element(By.XPATH, "//div[1]/div/h1/span/span").text == "Enter your phone number or email address":
                print("Suspicious login attempt detected, attempting to enter email on login prochedures.")
                if self.email is None:
                    raise ValueError("Email is required due to suspicious login attempt, but email is not provided on credentials!")
                email_input = self.driver.find_element(By.XPATH, "//input")
                for i in self.email:
                    email_input.send_keys(i)
                    time.sleep(rd.uniform(0.05, 0.2))
                self.driver.find_element(By.XPATH, "//div[2]/div/div/div/button").click()
        except:
            pass

        # Put password
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//input[@name='password']")))
        password_input = self.driver.find_element(By.XPATH, "//input[@name='password']")
        for i in self.password:
            password_input.send_keys(i)
            time.sleep(rd.uniform(0.05, 0.2))
        self.driver.find_element(By.XPATH, "//button[@data-testid='LoginForm_Login_Button']").click()
        time.sleep(5)

        warnings.warn("Please zoom out te browser to 25%, thus there'll be more posts loaded per scroll", UserWarning)
        print("Login sucess!")
        wait(10)

    def start(self, filters, startDate: str = "", endDate: str = "",
              scraping_Params  =  {"wait_short": 10, "wait_long": 30,
                                  "detection_wait": 900, "max_empty_pages": 2},
                                  saveFormat: Literal["csv", "json", "both"] = "csv", 
                                  autoSave: bool = False, autoSaveInterval: int = 15, continue_if_timeout: bool = True,
                                  processDir: str = "", resume_from_savepoint: bool = True) -> None:
        '''
        This function is used to start the scrapping process based on the given filters.
        
        Parameters
        ----------
        - Filters : dict
            - A dictionary containing the filters for scrapping.
            - The dictionary should be in the following format:
            ```
            {
                "all_these_words": "",
                "this_exact_phrase": "",
                "any_of_these_words": "",
                "none_of_these_words": "",
                "these_hashtags": "", 
                "from_accounts": "",            
                "to_accounts": "",              
                "mentioning_accounts": "",
                "language": "",   
                "Minimum_replies": "",
                "Minimum_likes": "",
                "Minimum_retweets": "",
                "links": True,
                "replies": True,                
            }
            ```
        - startDate : str
            - The latest date for scrapping in the format "YYYY-MM-DD".
            - If empty, will default to current date.
        
        - endDate : str
            - The earliest date for scrapping in the format "YYYY-MM-DD".
            - If empty, will default to "2006-01-01" (Twitter launch date).
        
        - scraping_Params : dict
            - A dictionary containing the scrapping parameters.
            - The dictionary should be in the following format:
            ```
            {
                "wait_short": 10,
                "wait_long": 30,
                "detection_wait": 900,
                "max_empty_pages": 2
            }
            ```
        - wait_short : int
            - Short wait time in seconds for page loading. Used for normal page loads. E.g, scrollig down to load more posts

        - wait_long : int
            - Long wait time in seconds for page loading. Used for cases where the page takes longer to load. Like after getting into a new page
            
        - detection_wait : int
            - Wait time in seconds when scraping detection is encountered.

        - max_empty_pages : int
            - Maximum number of consecutive empty pages before stopping scrapping.

        - saveFormat : Literal["csv", "json", "both"]
            - The format to save the scrapped data. Can be "csv", "json", or "both".
            - Default is "csv".

        - autoSave : bool
            - Whether to automatically save the scrapped data at regular intervals.
            - Default is False.

        - autoSaveInterval : int
            - The interval to automatically save the scrapped data based on how many posts have been scraped.
            - Default is 15.

        - continue_if_timeout : bool
            - Whether to continue scrapping if scraping detection is encountered.
            - Default is True.

        - processDir : str
            - The directory to save the scrapped data.
            - If empty, will default to current date in "YYYY-MM-DD" format.

        - resume_from_savepoint : bool
            - Whether to resume scrapping from the latest savepoint if available.
            - Default is True.

        '''
        self.SEARCH_URL = "https://x.com/search?q="
        
        # Adjust filters values
        filters["this_exact_phrase"] = f'\"{filters["this_exact_phrase"]}\"' if filters["this_exact_phrase"] != "" else ""
        _any_terms = []
        _any_raw = filters["any_of_these_words"].strip()
        if _any_raw:
            for g1, g2, g3 in re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', _any_raw):
                _any_terms.append(g1 or g2 or g3)
        filters["any_of_these_words"] = (
            f'({" OR ".join(_any_terms)})' if _any_terms else ""
        )
        filters["none_of_these_words"] = f'{" ".join(f"-{i}" for i in filters["none_of_these_words"].split())}' if filters["none_of_these_words"] != "" else ""
        filters["these_hashtags"] = f'({" OR ".join(f"{i}" for i in filters["these_hashtags"].split())})' if filters["these_hashtags"] != "" else ""

        filters["from_accounts"] = f'({" OR ".join(f"from:{i}" for i in filters["from_accounts"].split())})' if filters["from_accounts"] != "" else ""
        filters["to_accounts"] = f'({" OR ".join(f"to:{i}" for i in filters["to_accounts"].split())})' if filters["to_accounts"] != "" else ""
        filters["mentioning_accounts"] = f'({" OR ".join(f"@{i}" for i in filters["mentioning_accounts"].split())})' if filters["mentioning_accounts"] != "" else ""

        filters["language"] = f'lang:{lang_codes[filters["language"]]}' if filters["language"] != "" else ""
        filters["replies"] = "" if filters["replies"] else "-filter:replies" 
        filters["links"] = "" if filters["links"] else "-filter:links"

        filters["Minimum_replies"] = f'min_replies:{filters["Minimum_replies"]}' if filters["Minimum_replies"] != "" else ""
        filters["Minimum_likes"] = f'min_faves:{filters["Minimum_likes"]}' if filters["Minimum_likes"] != "" else ""
        filters["Minimum_retweets"] = f'min_retweets:{filters["Minimum_retweets"]}' if filters["Minimum_retweets"] != "" else ""

        FILTERS_COMBINATION = ""
        for _, value in filters.items():
            if value != "":
                FILTERS_COMBINATION += f'{value} '

        self.FILTERS_COMBINATION = quote(FILTERS_COMBINATION.strip())

        # Dates handling
        if startDate == "":
            startDate = int(datetime.now().timestamp())
        else:
            startDate = int(datetime.strptime(startDate, "%Y-%m-%d").timestamp())
        if endDate == "":
            endDate = int(datetime(2006, 1, 1).timestamp())   # Twitter launch date
        else:
            endDate = int(datetime.strptime(endDate, "%Y-%m-%d").timestamp())
        self.start_date = startDate
        self.end_date = endDate

        # scraping params
        self.WAIT_SHORT = scraping_Params["wait_short"]
        self.WAIT_LONG = scraping_Params["wait_long"]
        self.DETECTION_WAIT = scraping_Params["detection_wait"]
        self.MAX_EMPTY_PAGES = scraping_Params["max_empty_pages"]

        # Other params
        self.saveFormat = saveFormat
        self.autoSave = autoSave
        self.autoSaveInterval = autoSaveInterval
        self.continue_if_timeout = continue_if_timeout
        self.processDir = processDir if processDir != "" else datetime.now().strftime('%Y-%m-%d')
        
        if resume_from_savepoint:
            self._load_latest_savepoint()
        
        self.scrape()   # Immidiately start scraping right here right fucking now
        
    def scrape(self) -> None:
        '''
        Starts the scraping process.

        Raises
        ------
        - RuntimeError
            If scraping is detected and `continue_if_timeout` is False.
        - Exception
            For any other exceptions that occur during scraping including keyboard interrupts.
        '''
        reached_all_posts = False
        counter = 0
        seen = set()    # Uniqueness so there won't be a fuckton of duplicates

        # If there's already data on self.theDict, populate seen set. Used for resuming from savepoint
        if all(k in self.theDict for k in ("post_text", "Date", "User")) and self.theDict["post_text"]:
            seen = {
                (self.theDict["post_text"][i], self.theDict["Date"][i], self.theDict["User"][i])
                for i in range(len(self.theDict["post_text"]))
            }
        start_date = self.start_date

        try:
            while True:

                # Get the current date upper limit
                current_date_limit = start_date
                current_date_limit_str = datetime.fromtimestamp(current_date_limit).strftime("%Y-%m-%d")

                # If all shits been scraped, will save and break
                if reached_all_posts:
                    print("All posts have been scraped!")
                    # Delete all temps aka Savepoints
                    shutil.rmtree(f'Process/{self.processDir}/Savepoints/')
                    self.save("final")
                    break

                self.driver.get(self._build_search_url(current_date_limit))
                time.sleep(self.WAIT_SHORT)

                # CHECKER
                ##  1 CHECKER FOR SCRAPING DETECTION, IF `continue_if_timeout` IS TRUE, WILL WAIT AND CONTINUE, ELSE WILL JUST STOP.
                if self.continue_if_timeout:
                    if self._scrape_detected():
                        print("Scraping detected! Auto-saving progress...")
                        self.save("savepoint")
                        print(f"Waiting for {self.DETECTION_WAIT} seconds")
                        # Wait for abyssmal amount of time
                        wait(self.DETECTION_WAIT)
                        continue

                else:
                    if self._scrape_detected():
                        self.save("savepoint")
                        raise RuntimeError("Scraping detected! All progress have been saved.")

                ##  2 CHECKER FOR NO POSTS FOUND, IF SHIT HAPPENS WILL ROLE BACK FOR LIKE A DAY. IF SHIT KEEPS HAPPENING TILL `MAX_EMPTY_PAGES``, WILL STOP.
                start_date, counter, reached_all_posts = self._wait_for_posts(start_date, counter)
                if reached_all_posts:
                    print("No more posts found!")
                    continue

                last_height = self.driver.execute_script("return document.body.scrollHeight")

                while True:
                    elements = self.driver.find_elements(By.XPATH, '//div[@aria-label="Timeline: Search timeline"]/div/div')

                    for element in elements[:-1]:
                        try:
                            post_text, quoted_text, post_user, post_date = self._extract_post_data(element)
                        except (NoSuchElementException, StaleElementReferenceException):
                            continue

                        key = (post_text, post_date, post_user)
                        if key in seen:
                            continue

                        # If end date is reached, functional if user specified end_date at self.start()
    
                        if self.theDict["Date"] and safelyTurnStrToUnixTime(self.theDict["Date"][-1]) < self.end_date:
                            reached_all_posts = True
                            break
                        
                        seen.add(key)
                        self.theDict["post_text"].append(post_text)
                        self.theDict["quotedPost_text"].append(quoted_text)
                        self.theDict["User"].append(post_user)
                        self.theDict["Date"].append(post_date)

                        for group in element.find_elements(By.XPATH, './/div[@role="group"]'):
                            self.theDict["Reply_count"].append(
                                safe_int_from_aria(group.find_element(By.XPATH, './/div[1]/button').get_attribute("aria-label"))
                            )
                            self.theDict["Repost_count"].append(
                                safe_int_from_aria(group.find_element(By.XPATH, './/div[2]/button').get_attribute("aria-label"))
                            )
                            self.theDict["Like_count"].append(
                                safe_int_from_aria(group.find_element(By.XPATH, './/div[3]/button').get_attribute("aria-label"))
                            )
                            self.theDict["View_count"].append(
                                safe_int_from_aria(group.find_element(By.XPATH, './/div[4]/a').get_attribute("aria-label"))
                            )

                        if self.autoSave and len(seen) % self.autoSaveInterval == 0:
                            self.save("savepoint")
                        
                    if reached_all_posts:
                        break
                        
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(self.WAIT_SHORT)
                    new_height = self.driver.execute_script("return document.body.scrollHeight")

                    if new_height == last_height:
                        if self.theDict["Date"]:
                            last_date_only = safelyTurnStrToUnixTime(self.theDict["Date"][-1])
                            if last_date_only >= current_date_limit:
                                start_date = minOneDay(last_date_only)
                            else:
                                start_date = last_date_only
                        else:
                            start_date = current_date_limit

                        self.start_date = start_date
                        break

                    last_height = new_height

        except Exception as e:
            print(f"An error occurred: {e}")
            print("Auto-saving progress before exiting...")
            self.save("savepoint")
            self.driver.quit()
            raise e