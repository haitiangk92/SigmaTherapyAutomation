from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
from twilio.rest import Client
from MyVariables import Variables

FIRST_PASS = True
vars = Variables().vars

driver = webdriver.Chrome(vars["CHROME_DRIVER"])
driver.maximize_window()
SIGMA_URL = vars["SIGMA_URL"]
outFile = ""

class TherapyRecord():
    def __init__(self):
        self.start = ""
        self.end = ""

    def to_string(self):
        return f"Start - {self.start}\nEnd - {self.end}"

def inititalize():
    global outFile
    account_Code = vars["MOMS_ACCT"]
    users_Name = vars["MOMS_USERNAME"]
    users_RawPassword = vars["MOMS_PASSWORD"]
    
    driver.get(SIGMA_URL)
    
    time.sleep(3)

    acct = driver.find_element_by_id('accountID')
    acct.send_keys(account_Code)

    usr = driver.find_element_by_id('usersID')
    usr.send_keys(users_Name)
    
    pwrd = driver.find_element_by_id('usersPassword')
    pwrd.send_keys(users_RawPassword)
    
    search = driver.find_element_by_id('submitButton')
    search.click()

    try:
        outFile = open("patient_output.csv", "r")
        outFile.close()
        outFile = open("patient_output.csv", "a")
    except FileNotFoundError as ex:
        print(ex)
        try:
            outFile = open("patient_output.csv", "w")
            outFile.write("Patient Info,,Date Range,,Physical Therapy,,Occupational Therapy,,Speech Therapy\n")
            outFile.write("Last Name,First Name,Start,Finish,Start,Finish,Start,Finish,Start,Finish\n")
        except Exception as ex:
            print(ex)
            quit()

def find_newer_date(str1, str2):
    temp_str1 = str1.split("/")
    temp_str2 = str2.split("/")
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

def sendErrorText(theMessage):
    client = Client(vars["TWILIO_SID"], vars["TWILIO_TOKEN"])

    client.messages.create(
        to = vars["MY_CELL"],
        from_ = vars["TWILIO_NUMBER"],
        body = str(theMessage)
    )        

def create_record(last,first,starting,ending):
    global FIRST_PASS
    dashboard = driver.find_element_by_name("Main")
    driver.switch_to.frame(dashboard)
    
    if FIRST_PASS:
        FIRST_PASS = False
        resident = driver.find_element_by_link_text("Resident")
        resident.click()
        time.sleep(1)

    select = driver.find_element_by_partial_link_text("Select Resident")
    select.click()

    time.sleep(1)

    driver.switch_to.default_content()
    search_frame = driver.find_element_by_name("Main")
    driver.switch_to.frame(search_frame)

    inputs = driver.find_elements_by_tag_name("input")
    
    lastName = inputs[1]
    lastName.send_keys(last)
    
    status = inputs[11]
    status.clear()
    status.send_keys(Keys.BACKSPACE)

    searchBtn = driver.find_element_by_id("Search")
    searchBtn.click()

    time.sleep(1)

    try:
        results = driver.find_elements_by_partial_link_text(f"{last}, {first}")
        results += driver.find_elements_by_partial_link_text(f"{last}, {first}".upper())

        if len(results) == 0:
            throw_error = results[0]
    except Exception as ex:
        error = f"Patient Not found: {last}, {first}"
        sendErrorText(error)
        print(error + "\n")
        print("Verify the patient name and enter below")
        temp_last = input("Last Name: ")
        temp_first = input("First Name: ")
        driver.switch_to.default_content()

        return create_record(temp_last, temp_first,starting, ending)

    if len(results) > 1:
        for i in range(len(results)):
            print(f"{i + 1}. {results[i].text}")

        sendErrorText(f"Mutiple patients with name '{results[0].text}' were found")
        selected = int(input("Select the correct patient: ")) - 1
        time.sleep(1)
        results[selected].click()
    else:
        results[0].click()

    time.sleep(2)

    driver.switch_to.default_content()
    history_frame = driver.find_element_by_name("Main")
    driver.switch_to.frame(history_frame)

    try:
        okBtn = driver.find_element_by_id("ObjectHolder_Auto2_OKButton")
        okBtn.click()
    except:
        pass

    history = driver.find_element_by_partial_link_text("History")
    history.click()

    time.sleep(2)

    driver.switch_to.default_content()
    
    return search_history(last,first,starting,ending)

def search_history(last,first,starting, ending):    
    info_frame = driver.find_element_by_name("Main")
    driver.switch_to.frame(info_frame)

    inputs = driver.find_elements_by_tag_name("input")

    start_date = inputs[4]
    start_date.clear()

    end_date = inputs[5]
    end_date.clear()

    start_date.send_keys(starting)
    end_date.send_keys(ending)

    treament_type = inputs[8]
    treament_type.clear()
    treament_type.send_keys("Rehabilitation Clarification")
    treament_type.send_keys(Keys.RETURN)

    time.sleep(2)

    pys_record = TherapyRecord()        
    occ_record = TherapyRecord()
    spk_record = TherapyRecord()

    therapy = {
        "Physical" : pys_record,
        "Occupational" : occ_record,
        "Speech" : spk_record
    }

    try:
        rows = driver.find_elements_by_xpath('//*[@id="StdFilter_Table"]/tbody/tr')
        
        temp = []
        for i in range(len(rows) - 2):
            temp.append(rows.pop())

        rows = temp

        for row in rows:
            info = row.text
            lines = info.split("\n")

            for key in therapy.keys():
                if key in lines[2]:
                    if "until" in lines[3]:
                        if therapy[key].start == "":
                            therapy[key].start = lines[0].split(" ")[0]
                        
                        temp_end = lines[3].split(" ")[-1]
                        therapy[key].end = temp_end if therapy[key].end == "" else find_newer_date(therapy[key].end,temp_end)
                    break
    except Exception as ex:
        sendErrorText(f"No Records found for '{last}, {first}' between {starting} and {ending}.")
        print(ex)

    total_data = []
    for key in therapy.keys():
        total_data.append(therapy[key])
        print(f"{key}: \n{therapy[key].to_string()}")

    driver.switch_to.default_content()
    return total_data

def writeOutResults(params, results):
    times = ""

    for result in results:
        start_time = result.start if result.start != '' else '-'
        end_time = result.end if result.end != '' else '-'
        times += f",{start_time},{end_time}"

    out_line = f"{params[0]},{params[1]},{params[2]},{params[3]}{times}\n"
    
    print(out_line)
    outFile.write(out_line)

if __name__ == "__main__":
    while True:
        in_type = int(input("Enter the input type.\nSingle Patient: 1\nList: 2\n"))

        if in_type == 1 or in_type == 2:
            break
        else:
            print("\nThe Value must be 1 or 2\n\n")

    inititalize()
    last_patient = ""
    time.sleep(3)

    if in_type == 1:
        last = input("Last Name: ")
        first = input("First Name: ")
        starting = input("Start Time: ")
        ending = input("End Time: ")

        params = [last,first,starting,ending]

        writeOutResults(params, create_record(last,first,starting,ending))

    elif in_type == 2:
        try:
            theFile = open("patients.csv", "r")
            patients = theFile.readlines()
        except FileNotFoundError as ex:
            print(f"Patient File not found: {ex}")
            quit()

        for patient in patients:
            params = patient.split(",")

            if last_patient == f"{params[0]},{params[1]}":
                writeOutResults(params,search_history(params[0], params[1], params[2], params[3]))
            else:
                writeOutResults(params,create_record(params[0], params[1], params[2], params[3]))

            last_patient = f"{params[0]},{params[1]}"
    
    driver.quit()