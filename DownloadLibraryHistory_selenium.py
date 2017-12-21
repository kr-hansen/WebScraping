#Code for finding and printing webpages
#Need to have installed with webdriver in path.  Instructions at http://selenium-python.readthedocs.io/installation.html
#Pre-load stuff
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
from bs4 import BeautifulSoup
import os
import pandas as pd

#User Inputted Values
#Input Login Values
UserInputs = pd.read_csv("UserInfo.txt", header=None)
cardNum = UserInputs[0][0]
pin = UserInputs[0][1]
#Working Directory for Saving Location
savedir = UserInputs[0][2]
os.chdir(savedir)
#Select a File Name to Save Output
outFile = UserInputs[0][3]  

#Start Driver
driver = webdriver.Firefox()

#Get to Starting URL
url = UserInputs[0][4]
driver.get(url)
assert UserInputs[0][5] in driver.title

#Navigate to Account Login Page
accountButton = driver.find_element_by_css_selector("a[href*='myaccount']")
driver.get(accountButton.get_property('href'))
time.sleep(2)

#Input and execute Login
cardInput = driver.find_element_by_id("code")
cardInput.send_keys(cardNum)
pinInput = driver.find_element_by_id("pin")
pinInput.send_keys(pin)
submitButton = driver.find_element_by_css_selector("span.buttonSpriteSpan2")
submitButton.click()
time.sleep(4)

#Navigate to Book List
patronLink = driver.find_element_by_css_selector("a.myAccountLink")
patronLink.click()
time.sleep(2)
historyLink = driver.find_element_by_id("webpacFuncDirectLinkComponent_1")
historyLink.click()
time.sleep(2)

#Move to Table Storage Page and get Table Limits
historyFrame = driver.find_element_by_css_selector("iframe#accountContentIframe")
driver.get(historyFrame.get_attribute('src'))
pageSelector = driver.find_element_by_css_selector('td.browsePager')
pageElements = pageSelector.find_elements_by_css_selector('a')
numPages = len(pageElements)

#Extract Data page by page
bookHistory = []
for pg in range(numPages):
    tableBody = driver.find_element_by_css_selector('tbody')
    pgSoup = BeautifulSoup(tableBody.get_attribute('outerHTML'),'lxml') #Extract HTML
    titleList = pgSoup.find_all(class_='patFuncTitleMain')
    authorList = pgSoup.find_all(class_='patFuncAuthor')
    dateList = pgSoup.find_all(class_='patFuncDate')
    detailList = pgSoup.find_all(class_='patFuncDetails')
    #Loop through each list
    for (tit, au, dt, det) in zip(titleList, authorList, dateList, detailList):
        a = str(au).split('>')[1]
        author = a.split('<')[0]
        d = str(dt).split('>')[1]
        date = d.split('<')[0]
        de = str(det).split('>')[1]
        rawDetails = de.split('<')[0]
        t = str(tit).split('>')[1]
        rawTitle = t.split('<')[0]
        if '/' in rawTitle:
            splitTitle = rawTitle.split('/')
            title = splitTitle[0]
            titleDeets = splitTitle[1]
            details = rawDetails + ' / ' + titleDeets
        else:
            title = rawTitle
            details = rawDetails
        bookHistory.append((title,author,date,details))
    if pg < (numPages-1):
        nextButton = driver.find_element_by_xpath("//*[contains(text(), 'Next')]")
        nextButton.click() #Click to move to next page
        time.sleep(2)

#Convert list to Pandas Data Frame
labels = ['Title', 'Author', 'Date', 'Details']
df = pd.DataFrame.from_records(bookHistory, columns=labels);
df.to_csv(outFile)

#Close Webdriver
driver.quit()
