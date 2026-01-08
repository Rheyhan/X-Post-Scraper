import pandas as pd
from bs4 import BeautifulSoup
import json
import time
import numpy as np
from tqdm import tqdm
from typing import *
import re
import os
import glob
from IPython.display import clear_output

# Scrapping and crawling modules
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from user_agent import generate_user_agent
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
from urllib.parse import quote

#Credentials
with open("Credentials/twitter.json", "r") as f:
    credentials = json.load(f)

username = credentials["username"]
password = credentials["password"]
mail = credentials["email"]

def getTime(str):
    '''
    This function is used to convert string of datetime in isoformat to datetime object
    Params:
        str:
            - String of datetime in isoformat
    return:
        date_time_obj:
            - Datetime object
    '''
    date_time_obj = datetime.fromisoformat(str)
    date_time_obj =date_time_obj + timedelta(hours=7)
    return date_time_obj

def minOneDay(str):
    '''
    This function is used to subtract one day from the given date
    Params:
        str:
            - String of datetime in isoformat
    return:
        str:
            - String of datetime in isoformat after subtracting one day
    '''
    str = datetime.strptime(str, "%Y-%m-%d")
    str = str - timedelta(days=1)
    str = str.strftime("%Y-%m-%d")
    return str

def wait(timeout: int = 10):
    '''
    just a glorified simple function to wait for a certain amount of time
    '''
    for i in tqdm(range(timeout), desc="Waiting"):
        time.sleep(1)
    clear_output()  
    
class twitterScrapper:
    def __init__(self, username, password, email):
        '''
        This function is used to initialize the class
        Params:
            username:
                - Username of the twitter account
            password:
                - Password of the twitter account
            email:
                - Email of the twitter account
        '''
        self.username = username
        self.password = password
        self.email = email
        self.theDict = { "User" : [], "Date" : [], "Text" : [],
                         "Reply": [], "Repost": [], "Like": [], "View": []}
        self.login()
    
    def login(self):
        '''
        This function is used to initialize the driver and login to the twitter account
        '''
        loginURL = 'https://x.com/i/flow/login?redirect_after_login=%2Fsearch%3Fq%3Disrael%26src%3Dtyped_query%26f%3Dlive%26mx%3D2'
        
        # Initialize the driver
        usergAgent = generate_user_agent(device_type="desktop", os="win", navigator="chrome", platform="win")
        options = Options()
        options.add_argument(f'user-agent={usergAgent}')
        self.driver = webdriver.Chrome()
        self.driver.get(loginURL)

        # Login handling
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//input[@autocomplete = 'username']")))
        self.driver.find_element(By.XPATH, "//input[@autocomplete = 'username']").send_keys(self.username)
        self.driver.find_element(By.XPATH, "//div/button[2]").click()
        time.sleep(5)               # This will wait for the next login pop-up to appear

        # if email is neeeded. This means you logged a lot to the account and X raises a suspicious login attempt.
        try:
            if self.driver.find_element(By.XPATH, "//div[1]/div/h1/span/span").text == "Enter your phone number or email address":
                print("Suspicious login attempt detected, attempting to enter email on login prochedures.")
                self.driver.find_element(By.XPATH, "//input").send_keys(self.email)
                self.driver.find_element(By.XPATH, "//div[2]/div/div/div/button").click()
        except:
            pass
        
        # Put password
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//input[@name='password']")))
        self.driver.find_element(By.XPATH, "//input[@name='password']").send_keys(self.password)
        self.driver.find_element(By.XPATH, "//button[@data-testid='LoginForm_Login_Button']").click()
        time.sleep(5)
        print("zoom out 25%!")      # Please zoom out 25% manually in order to get more tweets loaded
        print("Login sucess!")
        wait(10)
    
    def searchAndscrap(self, keyword, startDate, endDate, continueifTimeout = True):
        '''
        This function is used to load the post and scrap the data
        Params:
            keyword:
                - Keyword to search need to be encoded beforehand
            startDate:
                - Start date of the search
            endDate:
                - End date of the search
        '''
        notTimeout = True
        notDateReached = True 
        
        while True:
            if not notDateReached:
                print("startDate has been reached!")
                pd.DataFrame(self.theDict).to_csv(f'Completed.csv', index=False)
                break
            
            untilDate = endDate
            searchLink = f"https://x.com/search?q={keyword}%20until%3A{untilDate}%20since%3A{startDate}&src=typed_query&f=live"
            self.driver.get(searchLink)
            
            # This will check if scrapping is detected, if it is. It'll wait for 20 mins
            if continueifTimeout:
                try:
                    #   This is essential to check if the scrapping is detected
                    WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Home timeline"]/div/div/div/span[@style="text-overflow: unset;"]')))
                    print("Saving!")
                    pd.DataFrame(self.theDict).to_csv(f'Savepoints/{untilDate}.csv', index=False)
                    print("Scrapping detected, waiting for 15 mins")
                    for i in tqdm(range(900), desc="Waiting"):
                        time.sleep(1)
                    clear_output()
                    continue
                except:
                    pass
            if not continueifTimeout:
                try:
                    WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Home timeline"]/div/div/div/span[@style="text-overflow: unset;"]')))
                    notTimeout = False
                except:
                    pass
                if not notTimeout: break
            
            # This will wait for the page to load, if nothing exists. Minus one day and repeat
            try:
                WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@data-testid='cellInnerDiv']")))   # Initialize
            except:
                endDate = minOneDay(endDate)
                continue
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            while True:

                elements = self.driver.find_elements(By.XPATH, '//div[@aria-label="Timeline: Search timeline"]/div/div')
                
                for element in elements[:-1]:
                    
                    # Check if text exists, if not then continue.  
                    try:
                        text = ''.join([i.text for i in element.find_elements(By.XPATH, './/div[@data-testid="tweetText"]/span')])
                    except:
                        continue
                    if text in self.theDict["Text"]:
                        continue
                    
                    
                    # TODO: Get date and check if theDate is lower than startDate. Break entire loop
                    theDate = getTime(element.find_element(By.XPATH, './/time').get_attribute("datetime"))
                    
                    # append text
                    self.theDict["Text"].append(text)
                    
                    # append user
                    self.theDict["User"].append(element.find_element(By.XPATH, './/a/div/span').text)
                    
                    # append Date
                    self.theDict["Date"].append(theDate.strftime("%Y-%m-%d-%H:%M:%S"))
                    
                    # post attrs
                    for group in element.find_elements(By.XPATH, './/div[@role="group"]'):
                        self.theDict["Reply"].append(int(re.search(r'\d+', group.find_element(By.XPATH, './/div[1]/button').get_attribute("aria-label"))[0]))
                        self.theDict["Repost"].append(int(re.search(r'\d+', group.find_element(By.XPATH, './/div[2]/button').get_attribute("aria-label"))[0]))
                        self.theDict["Like"].append(int(re.search(r'\d+',group.find_element(By.XPATH, './/div[3]/button').get_attribute("aria-label"))[0]))
                        self.theDict["View"].append(int(re.search(r'\d+', group.find_element(By.XPATH, './/div[4]/a').get_attribute("aria-label"))[0]) if re.search(r'\d+', group.find_element(By.XPATH, './/div[4]/a').get_attribute("aria-label")) else 0)
                
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(5)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # This check if startdate has been reached, thus breaking the entire function.
                if getTime(self.theDict["Date"][-1]) < getTime(startDate):
                    notDateReached = False
                    break
                
                # will break if the scrollbar is at the bottom
                if new_height == last_height:
                    endDate = '-'.join(self.theDict["Date"][-1].split("-")[:3])
                    # This will check if the untilDate is the same as endDate, if it is. It'll minus one day.
                    if untilDate == endDate:
                        endDate = minOneDay(endDate)
                    break
                
                last_height = new_height

if __name__ == "__main__":
    session = twitterScrapper(username, password, mail)
    session.searchAndscrap('"jokowi"%20(terimakasih%20OR%20terima%20kasih%20OR%20%23terimakasihjokowi)', "2010-01-01", "2024-09-29")