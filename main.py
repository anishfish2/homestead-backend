from flask import Flask, request
from flask_cors import CORS
import pandas as pd
import json
import openai
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/run-one")
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

@app.route("/get-suggestion")
def ask_gpt():
    load_dotenv()
    openai.api_key = os.getenv('OPENAI_KEY')

    sent = request.get_json()['factors']
    sent_merged = ""
    prompt = "A user has just used an app to determine whether they are eligible for a loan."

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

    response = openai.ChatCompletion.create(
    model="gpt-4",
    messages= [{"role": "user", "content": prompt}]
    )

    total = response['choices'][0]['message']['content']

    return total
