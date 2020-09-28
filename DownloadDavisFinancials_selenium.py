#Code for finding and printing webpages
#Need to have installed with webdriver in path.  Instructions at http://selenium-python.readthedocs.io/installation.html
#Pre-load stuff
import os
import pandas as pd
import numpy as np
import yaml
from selenium import webdriver
from bs4 import BeautifulSoup
import camelot

#User Inputted Parameters in filename in same directory
inputFile = "DavisFinancials.yaml"
with open(inputFile, 'r') as stream:
    params = yaml.load(stream, yaml.SafeLoader)

#Parse Inputs
url = params['Inputs']['website']
savedir = params['Outputs']['outputDir']
if os.path.isdir(savedir) == False:
    os.mkdir(savedir)

#Start Driver
driver = webdriver.Firefox()

#Get to Starting URL
driver.get(url)
assert params['Inputs']['confirmTitle'] in driver.title

#Specific TabPanel Role Elements to Extract
elContent = driver.find_elements_by_css_selector("section[role='tabpanel']")
nestedLinks = []
for el in elContent:
    nestedLinks.append(el.find_elements_by_tag_name('a'))

#Flatten all links to search through
elLinks = [el for sublist in nestedLinks for el in sublist]

#Find Links to only Financial Section Only PDFs
financialLinks = []
for idx, link in enumerate(elLinks):
    if params['Inputs']['PDFFindString'] in link.get_attribute('innerHTML'):
        financialLinks.append(link.get_attribute('href'))

#Loop through PDFs to extract tables
pdfDict = {}
for pdflink in financialLinks:
    driver.get(pdflink)
    pdfTables = camelot.read_pdf(driver.current_url, flavor='stream', pages='6-8', strip_text='$') #Read in Tables of Interest
    tabLoop = 0
    for table in pdfTables:
        if table.shape[1] > params['Inputs']['tableSizeThreshold']: #Keep only tables with more than X colums (Real Tables)
            for val in params['Inputs']['falseHeaderValues']:
                if val in table.data[0]: #If missed top row of header
                    top, bottom = table.rows[0]
                    newy1 = int(top + (top-bottom))
                    y2 = int(table.rows[-1][-1])
                    x1 = int(table.cols[0][0])
                    x2 = int(table.cols[-1][-1])
                    newtable = camelot.read_pdf(driver.current_url, flavor='stream', pages=str(table.page), strip_text='$', table_areas=['{0},{1},{2},{3}'.format(x1,newy1,x2,y2)])
                    table = newtable[0]
            for val in params['Inputs']['falseFooterValues']:
                if val in table.data[-1]: #If added extra falseFooterValues
                    top, bottom = table.rows[-1]
                    newy2 = int(top)
                    y1 = int(table.rows[0][0])
                    x1 = int(table.cols[0][0])
                    x2 = int(table.cols[-1][-1])
                    newtable = camelot.read_pdf(driver.current_url, flavor='stream', pages=str(table.page), strip_text='$', table_areas=['{0},{1},{2},{3}'.format(x1,y1,x2,newy2)])
                    table = newtable[0]
            #If captured too many additional rows in top header (Determined as only one value in 1 less than number of columns)
            extraHeaderRows = []
            for idx, row in enumerate(table.data[:params['Inputs']['maxHeaderRows']]):
                emptySpots = [i for i, x in enumerate(row) if x == '']
                if len(emptySpots) == len(row)-1:
                    extraHeaderRows.append(idx)
            curTable = table.df
            curTable = curTable.drop(index=extraHeaderRows)
            nHeader = curTable[0].eq('').sum() #Get Number of Header Rows
            if tabLoop == 0:
                tabName = params['Inputs']['tableName0'] + curTable.iloc[nHeader-1,-1]
            elif tabLoop == 1:
                tabName = params['Inputs']['tableName1'] + curTable.iloc[nHeader-1,-1]
            if tabName == 'ChangeNetPos2016-2015': #Handle one annoying exception
                curTable.iloc[:2,4] = curTable.iloc[:2,5]
            #Drop columns that are empty on more than 3 quarters of rows
            emptyCols = table.df.columns[table.df.eq('').sum() > table.df.index.size*.75]
            curTable = curTable.drop(columns=emptyCols)
            curTable = curTable.rename(index=curTable[0]).drop(columns=0) #Rename first column to indexes
            nCols = curTable.columns.size
            for colidx in range(0,nCols-1,2): #Copy Subheaders for Blank Columns, skipping last column
                if curTable.iloc[:nHeader-1,colidx].eq('').sum() > 1:
                    curTable.iloc[:nHeader-1,colidx] = curTable.iloc[:nHeader-1,colidx+1]
                elif curTable.iloc[:nHeader-1,colidx+1].eq('').sum() > 1:
                    curTable.iloc[:nHeader-1,colidx+1] = curTable.iloc[:nHeader-1,colidx]
            columns = [curTable.iloc[:nHeader,col].str.cat(sep=' ').lstrip() for col in range(nCols)] #Concatenate Subheaders for Column Names
            curTable = curTable.iloc[nHeader:,:]
            curTable.columns = columns
            for col in curTable: #Clean up Strings to Convert to Floats
                curTable[col] = curTable[col].str.lstrip('$ \n') #Remove $ signs
                curTable[col] = curTable[col].str.replace('(','-').str.rstrip(')') #Make negatives negative
                curTable[col] = curTable[col].str.replace(',','') #Remove Commas
            curTable = curTable.astype('float64', errors='ignore') #Ignore Empty Fields and leave Empty
            #Add to Master Dict
            pdfDict[tabName] = curTable
            tabLoop += 1

#Save dictionary DataFrames to CSVs
os.chdir(savedir)
for key in pdfDict:
    pdfDict[key].to_csv(key+'.csv')

#Close Webdriver
driver.quit()
