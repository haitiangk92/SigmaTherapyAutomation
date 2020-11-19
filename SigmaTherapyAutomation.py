from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
from twilio.rest import Client
from MyVariables import Variables #Personal Module to manage personal information

FIRST_PASS = True #Keeping track of execution order
vars = Variables().vars 

driver = webdriver.Chrome(vars['CHROME_DRIVER'])
driver.maximize_window()

SIGMA_URL = vars['SIGMA_URL']
outFile = '' #Declaring the variable for the output file so its in the global scope

# Class for keeping a record for every kind of therapy
class TherapyRecord():
    def __init__(self):
        self.start = ''
        self.end = ''

    def to_string(self):
        return f'Start - {self.start}\nEnd - {self.end}'

# Instantiaing the driver and setting up the system for data
def inititalize():
    global outFile
    account_Code = vars['MOMS_ACCT']
    users_Name = vars['MOMS_USERNAME']
    users_RawPassword = vars['MOMS_PASSWORD']
    
    driver.get(SIGMA_URL) #Setting the url to the driver
    
    time.sleep(3) #Giving the page time to load

    #Getting the input element for the account name on the page and filling it in
    acct = driver.find_element_by_id('accountID')
    acct.send_keys(account_Code)

    #Getting the input element for the username on the page and filling it in
    usr = driver.find_element_by_id('usersID')
    usr.send_keys(users_Name)
    
    #Getting the input element for the password on the page and filling it in
    pwrd = driver.find_element_by_id('usersPassword')
    pwrd.send_keys(users_RawPassword)
    
    #Getting the element for the search button on the page and pressing it
    search = driver.find_element_by_id('submitButton')
    search.click()

    try: #Trying to instantiate the output file
        outFile = open('patient_output.csv', 'r')
        outFile.close()
        outFile = open('patient_output.csv', 'a')
    except FileNotFoundError as ex:
        print(ex)
        try: #Trying to create a new output file if one was not created or found already
            outFile = open('patient_output.csv', 'w')
            outFile.write('Patient Info,,Date Range,,Physical Therapy,,Occupational Therapy,,Speech Therapy\n')
            outFile.write('Last Name,First Name,Start,Finish,Start,Finish,Start,Finish,Start,Finish\n')
        except Exception as ex:
            print(ex)
            quit() #Quit if there is an error creating the file


# Takes two dates strings and compares them. 
#
# Returns the most recent date
def find_newer_date(str1, str2):
    temp_str1 = str1.split('/')
    temp_str2 = str2.split('/')
    if int(temp_str1[2]) == int(temp_str2[2]):
        if int(temp_str1[0]) == int(temp_str2[0]):
            if int(temp_str1[1]) == int(temp_str2[1]):
                return str1
            elif int(temp_str1[1]) > int(temp_str2[1]):
                return str1
            else:
                return str2
        elif int(temp_str1[0]) > int(temp_str2[0]):
            return str1
        else:
            return str2
    elif int(temp_str1[2]) > int(temp_str2[2]):
        return str1
    else:
        return str2

#Sends an error text message to me 
def sendErrorText(theMessage):
    client = Client(vars['TWILIO_SID'], vars['TWILIO_TOKEN'])

    client.messages.create(
        to = vars['MY_CELL'],
        from_ = vars['TWILIO_NUMBER'],
        body = str(theMessage)
    )        

def create_record(last,first,starting,ending):
    global FIRST_PASS #Gets access to change global varial

    #Finds and sets the focus to the html document for the Dashboard Frame
    dashboard = driver.find_element_by_name('Main')
    driver.switch_to.frame(dashboard)
    
    #Finds and selects the 'Resident' element if this is the first pass. Clicking on this element causes issues after the first pass, 
    #so this block will only be called once
    if FIRST_PASS:
        FIRST_PASS = False
        resident = driver.find_element_by_link_text('Resident')
        resident.click()
        time.sleep(1)

    #Getting the element for the Select Resident page link on the page and clicking it
    select = driver.find_element_by_partial_link_text('Select Resident')
    select.click()

    time.sleep(1) #Giving the page time to load

    #Switching the focus of the driver to html document for the Select Resident Frame
    driver.switch_to.default_content()
    search_frame = driver.find_element_by_name('Main')
    driver.switch_to.frame(search_frame)

    #Gets all of the inouts on the page
    inputs = driver.find_elements_by_tag_name('input')
    
    #Getting the input element for the patient last name on the page and filling it in
    lastName = inputs[1]
    lastName.send_keys(last)
    
    #Getting the input element for the patient status on the page and clears it
    status = inputs[11]
    status.clear()
    status.send_keys(Keys.BACKSPACE)

    #Getting the element for the search button on the page and clicks it
    searchBtn = driver.find_element_by_id('Search')
    searchBtn.click()

    time.sleep(1) #Gives the page time to load

    try: #Tries to find the patient in a list of results
        results = driver.find_elements_by_partial_link_text(f'{last}, {first}')
        results += driver.find_elements_by_partial_link_text(f'{last}, {first}'.upper())

        if len(results) == 0:
            throw_error = results[0]
    except Exception as ex: #Sends text to me, prompts the user for verified information and calls this function recursively with the new info 
        error = f'Patient Not found: {last}, {first}'
        sendErrorText(error)
        print(error + '\n')
        print('Verify the patient name and enter below')
        temp_last = input('Last Name: ')
        temp_first = input('First Name: ')
        driver.switch_to.default_content()

        return create_record(temp_last, temp_first,starting, ending)

    #If there is more than one result, a text message is sent to me incase I am not at the computer and prompts 
    #the user to select the correct patient after verification
    if len(results) > 1: 
        for i in range(len(results)):
            print(f'{i + 1}. {results[i].text}')

        sendErrorText(f'Mutiple patients with name "{results[0].text}" were found')
        selected = int(input('Select the correct patient: ')) - 1
        time.sleep(1)
        results[selected].click()
    else: #Selects the patient if there is only one
        results[0].click()

    time.sleep(2) #Gives the page time to load

    #Switching the focus of the driver to html document for the Patient Results Frame
    driver.switch_to.default_content()
    history_frame = driver.find_element_by_name('Main')
    driver.switch_to.frame(history_frame)

    try: #Checks for a pop up alert and clicks tye 'OK' Button
        okBtn = driver.find_element_by_id('ObjectHolder_Auto2_OKButton')
        okBtn.click()
    except: #Skips the click if the popup is not found
        pass

    #Finds the link to patient history and clicks it
    history = driver.find_element_by_partial_link_text('History')
    history.click()

    time.sleep(2) #Gives the page time to load


    #Switching the focus of the driver to Default
    driver.switch_to.default_content()
    
    return search_history(last,first,starting,ending)

def search_history(last,first,starting, ending): 
    #Switching the focus of the driver to html document for the Patient History Info Frame   
    info_frame = driver.find_element_by_name('Main')
    driver.switch_to.frame(info_frame)

    #Finds all of the inputs on the page
    inputs = driver.find_elements_by_tag_name('input')

    #Getting the input element for the patient start date on the page and clears it
    start_date = inputs[4]
    start_date.clear()

    #Getting the input element for the patient end date on the page and clears it
    end_date = inputs[5]
    end_date.clear()

    #Fills in the dates
    start_date.send_keys(starting)
    end_date.send_keys(ending)

    #Getting the input element for the patient treatment type on the page and filling it in
    treament_type = inputs[8]
    treament_type.clear()
    treament_type.send_keys('Rehabilitation Clarification')
    treament_type.send_keys(Keys.RETURN)

    time.sleep(2) #Gives the page time to load

    pys_record = TherapyRecord()        
    occ_record = TherapyRecord()
    spk_record = TherapyRecord()

    #Dictionary of Records
    therapy = {
        'Physical' : pys_record,
        'Occupational' : occ_record,
        'Speech' : spk_record
    }

    try: #Trys to get the list of therapy records
        result_rows = driver.find_elements_by_xpath('//*[@id="StdFilter_Table"]/tbody/tr')
        
        #Creates a list of the therapy results in chronilogical order
        rows = []
        for i in range(len(result_rows) - 2):
            rows.append(result_rows.pop())

        for row in rows: 
            #Gather the information and splits it accordingly for furthur parsing
            info = row.text
            lines = info.split('\n')

            for key in therapy.keys():
                #Checks for keyword 'until' to continue
                if key in lines[2]:
                    if 'until' in lines[3]:
                        #Parses information then stores it per therapy
                        if therapy[key].start == '':
                            therapy[key].start = lines[0].split(' ')[0]
                        
                        temp_end = lines[3].split(' ')[-1]
                        therapy[key].end = temp_end if therapy[key].end == '' else find_newer_date(therapy[key].end,temp_end)
                    break
    except Exception as ex: #Sends text messsage of no found records to me and alerts user
        sendErrorText(f'No Records found for "{last}, {first}" between {starting} and {ending}.')
        print(ex)

    #Creates the list to be returned
    total_data = []
    for key in therapy.keys():
        total_data.append(therapy[key])
        print(f'{key}: \n{therapy[key].to_string()}') #Debugging line

    #Switching the focus of driver to Default
    driver.switch_to.default_content()
    return total_data

#Takes the Patient information and record results to write the information to the output file
def writeOutResults(params, results):
    #Empty string for storing therapy dates
    dates = ''

    for result in results: #Builds the string
        start_date = result.start if result.start != '' else '-'
        end_date = result.end if result.end != '' else '-'
        dates += f',{start_date},{end_date}'

    #Line to write out
    out_line = f'{params[0]},{params[1]},{params[2]},{params[3]}{dates}\n'
    
    print(out_line) #Debugging Line
    outFile.write(out_line) #Writing to the output file

#Main function
if __name__ == '__main__':
    while True: #Taking in and verifying the input type
        in_type = int(input('Enter the input type.\nSingle Patient: 1\nList of Patients: 2\n'))

        if in_type == 1 or in_type == 2:
            break
        else:
            print('\nThe Value must be 1 or 2\n\n')

    inititalize() 
    last_patient = '' #Keeping track of the last patient
    time.sleep(3) #Gives the page time to load

    if in_type == 1: #Single patient input
        last = input('Last Name: ')
        first = input('First Name: ')
        starting = input('Start Time: ')
        ending = input('End Time: ')

        params = [last,first,starting,ending]

        writeOutResults(params, create_record(last,first,starting,ending))
    elif in_type == 2: #List of patients
        try: #Trying to locate and open the patient file  
            theFile = open('patients.csv', 'r')
            patients = theFile.readlines()
        except FileNotFoundError as ex: #Alerts the user that the file was not found and quits the program 
            print(f'Patient File not found: {ex}')
            quit()

        for patient in patients: #Goes through each patient on the list and ouputs the correct information
            params = patient.split(',')

            if last_patient == f'{params[0]},{params[1]}': #Skips the initial run through if it is the same patient
                writeOutResults(params,search_history(params[0], params[1], params[2], params[3]))
            else: #Runs normally otherwise
                writeOutResults(params,create_record(params[0], params[1], params[2], params[3]))

            #Sets the last patient
            last_patient = f'{params[0]},{params[1]}'
    
    #Exits the driver
    driver.quit()