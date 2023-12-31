from flask import Flask, request
from flask_cors import CORS
import pandas as pd
import json
import openai
from dotenv import load_dotenv
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


app = Flask(__name__)
CORS(app)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/run-one", methods=['POST'])
def analyze():

    data = pd.DataFrame.from_dict(request.get_json(), orient='index')

    data['LTV'] = data['loan_amount'] / data['appraised_value']

    def add_pmi(row):
        if row['LTV'] >= .8:
            return row['monthly_mortgage_payment'] + row['appraised_value'] * .01 / 12
        else:
            return row['monthly_mortgage_payment']
        
    data['monthly_mortgage_payment_processed'] = data.apply(add_pmi, axis = 1)

    data['DTI'] = (data['credit_card_payment'] + data['car_payment'] + data['student_loan_payments'] + data['monthly_mortgage_payment_processed']) / data['gross_monthly_income']

    data['FEDTI'] = data['monthly_mortgage_payment_processed'] / data['gross_monthly_income']

    print(data)
    #Determine approval
    def add_filter(df):
        approved_list = []
        ltv_list = []
        credit_score_list = []
        dti_43_list = []
        dti_36_list = []
        fedti_list = []

        for index, row in df.iterrows():
            approved = 'Y'
            note = []
            credit_score, ltv, dti_43, dti_36, fedti = 0, 0, 0, 0, 0

            if row['credit_score'] < 640:
                approved = 'N'
                credit_score = 1
            if row['LTV'] >= .8:
                ltv = 1
            if row['DTI'] >= .43:
                approved = 'N'
                dti_43 = 1
            elif row['DTI'] >= .36:
                approved = 'N'
                dti_36 = 1
            if row['FEDTI'] >= .28:
                approved ='N'
                fedti = 1

            approved_list.append(approved)
            credit_score_list.append(credit_score)
            ltv_list.append(ltv)
            dti_43_list.append(dti_43)
            dti_36_list.append(dti_36)
            fedti_list.append(fedti)

        df['approved'] = approved_list
        df['credit_score_check'] = credit_score_list
        df['ltv_check'] = ltv_list
        df['dti_43_check'] = dti_43_list
        df['dti_36_check'] = dti_36_list
        df['fedti_check'] = fedti_list
        
        return df
    
    data = add_filter(data)
    return data.to_json()


@app.route("/averages")
def return_averages():
    with open("averages.json", 'r') as file:
        data = json.load(file)
    return data

@app.route("/percent-rejected-by-factor")
def return_percent_by_factor():
    return (
        {
            "credit_score_check":4028/8400,
            "ltv_check": 6258/8400,
            "dti_43_check": 6526/8400,
            "dti_36_check": 1380/8400,
            "fedti_check": 6286/8400
        }
    )

@app.route("/get-suggestion", methods=['POST'])
def ask_gpt():
    load_dotenv()
    openai.api_key = os.getenv('OPENAI_KEY')

    sent = request.get_json()['factors']
    sent_merged = ""
    prompt = "A user has just used an app to determine whether they are eligible for a loan. "

    for i in sent:
        sent_merged += i

    if "credit" in sent_merged:
        prompt += "Currently, their credit score is below 640. "
    if "ltv" in sent_merged:
        prompt += "Currently, their LTV is greater or equal to 80%. "
    if "dti_43" in sent_merged:
        prompt += "Currently, their DTI is greater than 43%. "
    if "dti_36" in sent_merged:
        prompt += "Currently, their DTI is greater than 36 percent but less than 43%. "
    if "fedt" in sent_merged:
        prompt += "Currently, their FEDTI is greater than 28%. "

    
    prompt += "Can you reccomend some advice, tips, and suggestions as to what they might be able to change in order to get the loan approved? "

    print(prompt)

    start_time = time.time()

    response = openai.ChatCompletion.create(
    model="gpt-4",
    messages= [{"role": "user", "content": prompt}]
    )
    
    end_time = time.time()
    print("API call took {:.2f} seconds".format(end_time - start_time))

    total = response['choices'][0]['message']['content']

    print(total)
    return total



@app.route("/get-gross-approval")
def gross_approval():

    x_listN = []
    x_listY = []
    y_listN = []
    y_listY = []

    file_path = 'x_listN'  
    with open(file_path, 'r') as file:
        file_content = file.read()

        x_listN = file_content.split()

    file_path = 'x_listY'  
    with open(file_path, 'r') as file:
        file_content = file.read()

        x_listY = file_content.split()

    file_path = 'y_listN'  
    with open(file_path, 'r') as file:
        file_content = file.read()

        y_listN = file_content.split()

    file_path = 'y_listY'  
    with open(file_path, 'r') as file:
        file_content = file.read()

        y_listY = file_content.split()

    return ({"x_N" : x_listN,
             "x_Y" : x_listY,
             "y_N" : y_listN,
             "y_Y" : y_listY
             })

@app.route("/reverse-engineer", methods=['POST'])
def reverse_engineer():
   
    data = pd.DataFrame.from_dict([request.get_json()['value']])

    print(data.iloc[0])
    data['LTV'] = data['loan_amount'] / data['appraised_value']

    def add_pmi(row):
        if row['LTV'] >= .8:
            return row['monthly_mortgage_payment'] + row['appraised_value'] * .01 / 12
        else:
            return row['monthly_mortgage_payment']
        
    data['monthly_mortgage_payment_processed'] = data.apply(add_pmi, axis = 1)

    data['DTI'] = (data['credit_card_payment'] + data['car_payment'] + data['student_loan_payments'] + data['monthly_mortgage_payment_processed']) / data['gross_monthly_income']

    data['FEDTI'] = data['monthly_mortgage_payment_processed'] / data['gross_monthly_income']

    print(data)
    #Determine approval
    def add_filter(df):
        approved_list = []
        ltv_list = []
        credit_score_list = []
        dti_43_list = []
        dti_36_list = []
        fedti_list = []

        for index, row in df.iterrows():
            approved = 'Y'
            note = []
            credit_score, ltv, dti_43, dti_36, fedti = 0, 0, 0, 0, 0

            if row['credit_score'] < 640:
                approved = 'N'
                credit_score = 1
            if row['LTV'] >= .8:
                ltv = 1
            if row['DTI'] >= .43:
                approved = 'N'
                dti_43 = 1
            elif row['DTI'] >= .36:
                approved = 'N'
                dti_36 = 1
            if row['FEDTI'] >= .28:
                approved ='N'
                fedti = 1

            approved_list.append(approved)
            credit_score_list.append(credit_score)
            ltv_list.append(ltv)
            dti_43_list.append(dti_43)
            dti_36_list.append(dti_36)
            fedti_list.append(fedti)

        df['approved'] = approved_list
        df['credit_score_check'] = credit_score_list
        df['ltv_check'] = ltv_list
        df['dti_43_check'] = dti_43_list
        df['dti_36_check'] = dti_36_list
        df['fedti_check'] = fedti_list
        
        return df
    
    column_to_check = request.get_json()['change']


    data = add_filter(data)

    if data['approved'].iloc[0] == 'Y':
        return "Under your current parameters, your loan will get approved!"
    else:
        if column_to_check == "credit_score":
            temp = pd.DataFrame.from_dict([request.get_json()['value']])
            temp['credit_score'] = 641
            if add_filter(temp)['approved'][0] == 'Y':
                return ("Raise your credit score above 640 to approve your loan!")
            else:
                return ("It is not possible to approve your loan by increasing your credit score alone. Please try changing the other fields!")
        if column_to_check == "gross_monthly_income":
            temp = pd.DataFrame.from_dict([request.get_json()['value']]) 
            check_dti = (data['credit_card_payment'].iloc[0] + data['car_payment'].iloc[0] + data['student_loan_payments'].iloc[0] + data['monthly_mortgage_payment_processed'].iloc[0]) / .36
            check_fedti = data['monthly_mortgage_payment_processed'].iloc[0] / .28

            print(check_dti, check_fedti)
            if check_dti >= check_fedti:
                return f"You are limited by your DTI, raise your gross monthly income above {round(check_dti, 2)} to approve your loan!"
            else:
                return f"You are limited by your FEDTI, raise your gross monthly income above {round(check_fedti, 2)} to approve your loan!"
            
        
        if column_to_check == "appraised_value":
            temp = pd.DataFrame.from_dict([request.get_json()['value']]) 

            if data['DTI'].iloc[0] > .36:
                max_monthly_mortgage_payment_processed_dti = .36 * data['gross_monthly_income'].iloc[0] - data['credit_card_payment'].iloc[0] - data['car_payment'].iloc[0] - data['student_loan_payments'].iloc[0]
                max_monthly_mortgage_payment_processed_fedti = .28 * data['gross_monthly_income'].iloc[0]
                

                print(f"max_monthly_mortgage_payment_processed_dti: {max_monthly_mortgage_payment_processed_dti}")
                print(f"max_monthly_mortgage_payment_processed_fedti: {max_monthly_mortgage_payment_processed_fedti}")
                print(f"monthly_mortgage_processed: {data['monthly_mortgage_payment_processed'].iloc[0]}")
                print(f"monthly_mortgage: {data['monthly_mortgage_payment'].iloc[0]}")
                required_appraised_value = 0

                if data['LTV'].iloc[0] < .8 and data['monthly_mortgage_payment'].iloc[0] >= min(max_monthly_mortgage_payment_processed_dti, max_monthly_mortgage_payment_processed_fedti):
                    return f"You are limited by your monthly mortgage payment and cannot adjust the desired appraisal value to approve the loan!"
                elif data['LTV'].iloc[0] < .8 and data['monthly_mortgage_payment'].iloc[0] < min(max_monthly_mortgage_payment_processed_dti, max_monthly_mortgage_payment_processed_fedti):
                    return f"You approval should go through! Your monthly mortgage payment fits the requiements for fedti and dti!"
                else:
                    if data['monthly_mortgage_payment'].iloc[0] > min(max_monthly_mortgage_payment_processed_dti, max_monthly_mortgage_payment_processed_fedti):
                        return "Your monthly mortgage payment is above the maximum allowed to remain within DTI and FEDTI constraints"
                    else:
                        if max_monthly_mortgage_payment_processed_dti <= max_monthly_mortgage_payment_processed_fedti:
                            required_appraised_value = (max_monthly_mortgage_payment_processed_dti - data['monthly_mortgage_payment'].iloc[0]) * 12 / .01
                            if required_appraised_value >= 0:
                                return f"You are limited by your DTI, lower your appraised value below {required_appraised_value} to lower your monthly mortgage payment taking into account PMI to approve your loan!"
                            
                        else:
                            required_appraised_value = (max_monthly_mortgage_payment_processed_fedti - data['monthly_mortgage_payment'].iloc[0]) * 12 / .01 
                            return f"You are limited by your FEDTI, lower your appraised value below {required_appraised_value} to lower your monthly mortgage payment taking into account PMI to approve your loan!" 
    return "You are limited by another requirement parameter. It doesn't matter how much you change the given criteria, the loan will not be approved! Please try again!"

@app.route("/email", methods=['POST'])
def email():
    print(request.get_json())
    data = pd.DataFrame.from_dict([request.get_json()['value']])
    
    data['LTV'] = data['loan_amount'] / data['appraised_value']

    def add_pmi(row):
        if row['LTV'] >= .8:
            return row['monthly_mortgage_payment'] + row['appraised_value'] * .01 / 12
        else:
            return row['monthly_mortgage_payment']
        
    data['monthly_mortgage_payment_processed'] = data.apply(add_pmi, axis = 1)

    data['DTI'] = (data['credit_card_payment'] + data['car_payment'] + data['student_loan_payments'] + data['monthly_mortgage_payment_processed']) / data['gross_monthly_income']

    data['FEDTI'] = data['monthly_mortgage_payment_processed'] / data['gross_monthly_income']

    print(data)
    #Determine approval
    def add_filter(df):
        approved_list = []
        ltv_list = []
        credit_score_list = []
        dti_43_list = []
        dti_36_list = []
        fedti_list = []

        for index, row in df.iterrows():
            approved = 'Y'
            note = []
            credit_score, ltv, dti_43, dti_36, fedti = 0, 0, 0, 0, 0

            if row['credit_score'] < 640:
                approved = 'N'
                credit_score = 1
            if row['LTV'] >= .8:
                ltv = 1
            if row['DTI'] >= .43:
                approved = 'N'
                dti_43 = 1
            elif row['DTI'] >= .36:
                approved = 'N'
                dti_36 = 1
            if row['FEDTI'] >= .28:
                approved ='N'
                fedti = 1

            approved_list.append(approved)
            credit_score_list.append(credit_score)
            ltv_list.append(ltv)
            dti_43_list.append(dti_43)
            dti_36_list.append(dti_36)
            fedti_list.append(fedti)

        df['approved'] = approved_list
        df['credit_score_check'] = credit_score_list
        df['ltv_check'] = ltv_list
        df['dti_43_check'] = dti_43_list
        df['dti_36_check'] = dti_36_list
        df['fedti_check'] = fedti_list
        
        return df
    
    data = add_filter(data)

    print("got here before")        
    csv_filename = 'temp_data.csv'
    data.to_csv(csv_filename, index=False)

    load_dotenv()
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_username = 'anishfishy@gmail.com'
    smtp_password = os.getenv('EMAIL_PASS')

    from_email = 'anishfishy@gmail.com'
    to_email = request.get_json()['email']
    subject = 'Hello, world!'
    body = 'Please find your report down below.'

    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))
    print("got here")
    with open(csv_filename, "rb") as attachment:
        csv_attachment = MIMEApplication(attachment.read(), _subtype="csv")
        csv_attachment.add_header("Content-Disposition", f"attachment; filename={csv_filename}")
        message.attach(csv_attachment)
    print("here now")
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message( message)

    print("got here 2")
    os.remove(csv_filename)
    print(f"CSV file '{csv_filename}' deleted.")
    
    return data.to_json()


if __name__ == '__main__':
    app.run(debug=True, port=8000)