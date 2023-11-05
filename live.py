from flask import Flask, request
import pandas as pd
import json

app = Flask(__name__)

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
        lti_list = []
        credit_score_list = []
        dti_43_list = []
        dti_36_list = []
        fedti_list = []

        for index, row in df.iterrows():
            approved = 'Y'
            note = []
            credit_score, lti, dti_43, dti_36, fedti = 0, 0, 0, 0, 0

            if row['credit_score'] < 640:
                approved = 'N'
                credit_score = 1
            if row['LTV'] >= .8:
                lti = 1
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
            lti_list.append(lti)
            dti_43_list.append(dti_43)
            dti_36_list.append(dti_36)
            fedti_list.append(fedti)

        df['approved'] = approved_list
        df['credit_score_check'] = credit_score_list
        df['lti_check'] = lti_list
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