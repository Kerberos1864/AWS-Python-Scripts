# Monthly Cost Reporting using Lambda function

import boto3
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Create Cost Explorer service client using saved credentials
cost_explorer = boto3.client('ce')

#--------------------------------------------------------------------------------------------------
# Reporting periods

MONTHSBACK = 6
then = (datetime.now() - timedelta(days = MONTHSBACK*30))
today = datetime.now()

MONTHLY_START_DATE = (then.replace(day=1)).strftime('%Y-%m-%d')
MONTHLY_END_DATE = (today.replace(day=1)).strftime('%Y-%m-%d')

DAYSBACK = 8
COLUMNS = (MONTHSBACK * 2)
# START_DATE = (datetime.now() - timedelta(days = DAYSBACK)).strftime('%Y-%m-%d')
# END_DATE = (datetime.now()).strftime('%Y-%m-%d')
START_DATE =  (then.replace(day=1)).strftime('%Y-%m-%d')
END_DATE = (today.replace(day=1)).strftime('%Y-%m-%d')
YESTERDAY = (datetime.now() - timedelta(days = 1)).strftime('%Y-%m-%d')



MONTHLY_COST_DATES = [] # holder for dates used in monthly cost changes (every 1st of the month)
MONTHLY_COST_DATES2 = [] # holder for dates used in monthly cost changes (every 2nd of the month)

# This generates monthly dates (every 1st and 2nd of the month) going back 180 days
for x in range(180, 0, -1):

    if (datetime.now() - timedelta(days = x)).strftime('%d') == '01':
        temp_date = datetime.now() - timedelta(days = x)
        MONTHLY_COST_DATES.append(temp_date.strftime('%Y-%m-%d'))

        temp_date = datetime.now() - timedelta(days = x)
        MONTHLY_COST_DATES2.append(temp_date.strftime('%Y-%m-%d'))

print(MONTHLY_COST_DATES)
print(MONTHLY_COST_DATES2)

BODY_HTML = '<h2>AWS Monthly Cost Report for BPaaS Accounts - Summary</h2>'

#--------------------------------------------------------------------------------------------------
# Tuple for all the accounts listed in MEDailySpendView settings
accountMailDict = {
  'account_id_here' : 'email',
  'account_id_here' : 'email',
}

# Dictionary of named accounts
accountDict = {
  'account_id_here' : 'account_name_here',
  'account_id_here' : 'account_name_here',
}

# Create an account list based on dictionary keys
accountList = []
for key in accountDict.keys():
    #print(key)
    accountList.append(key)

# This list controls the number of accounts to have detailed report
# Accounts not listed here will be added to "Others". DO NOT remove 'Others' and 'dayTotal'
displayList = [
  'account_id_here',
  'account_id_here',
    'dayTotal'
]

displayListMonthly = [
  'account_id_here',
  'account_id_here',
  'monthTotal'
]


# Get cost information for accounts defined in accountDict

def ce_get_costinfo_per_account(accountDict_input):

    accountCostDict = {} # main dictionary of cost info for each account

    for key in accountDict_input:

        # Retrieve cost and usage metrics for specified account
        response = cost_explorer.get_cost_and_usage(
            TimePeriod={
                'Start': MONTHLY_START_DATE,
                'End': MONTHLY_END_DATE
            },
            Granularity='MONTHLY',
            Filter={
                'Dimensions': {
                    'Key': 'LINKED_ACCOUNT',
                    'Values': [
                        key,    # key is AWS account number
                    ]
                },
            },
            Metrics=[
                'UnblendedCost',
            ],
            #NextPageToken='string'
        )

        #print(response)

        periodCost = 0      # holder for cost of the account in reporting period

        # Calculate cost of the account in reporting period
        for dayCost in response['ResultsByTime']:
            #print(dayCost)
            periodCost = periodCost + float(dayCost['Total']['UnblendedCost']['Amount'])

        print('Cost of account ', key, ' for the period is: ', periodCost )

        # Only include accounts that have non-zero cost in the dictionary
        if periodCost > 0:
            accountCostDict.update({key:response})

    #print(accountCostDict)
    return accountCostDict

#--------------------------------------------------------------------------------------------------
# Create new dictionary and process totals for the reporting period

def process_costchanges_per_month(accountCostDict_input):
    reportCostDict = {}  # Main dictionary for displaying cost by month

    period = MONTHSBACK  # Define the number of months back you want to consider
    i = 0

    # Create a dictionary for every month of the reporting period
    while i < period:
        reportDate = (datetime.now() - timedelta(days=30 * (period - i)))
        month_key = reportDate.strftime('%Y-%m')
        reportCostDict[month_key] = {}
        i += 1

    print(reportCostDict)

    # Fill up each monthly dictionary with Account:Cost key-value pairs
    for key in accountCostDict_input:
        for dayCost in accountCostDict_input[key]['ResultsByTime']:
            start_date = dayCost['TimePeriod']['Start']
            month_key = start_date[:7]  # Extract the year-month part
            cost = float(dayCost['Total']['UnblendedCost']['Amount'])

            if key in reportCostDict[month_key]:
                reportCostDict[month_key][key]['Cost'] += cost
            else:
                reportCostDict[month_key][key] = {'Cost': cost}

    # Get the total cost for each reporting month
    for key in reportCostDict:
        monthTotal = sum(
            reportCostDict[key][account]['Cost'] for account in reportCostDict[key]
        )
        reportCostDict[key]['monthTotal'] = {'Cost': monthTotal}

    return reportCostDict













#--------------------------------------------------------------------------------------------------
# Create new dictionary for displaying/e-mailing the reporting period
# This takes the existing dictionary, displays accounts in displayList, and totals the
#   other accounts in Others.

def process_costchanges_for_display(reportCostDict_input):

    displayReportCostDict = {}      # holder for new dictionary

    # Enter dictionary report dates
    for reportDate in reportCostDict_input:
        displayReportCostDict.update({reportDate: None})
        displayReportCostDict[reportDate] = {}

        otherAccounts = 0.0     # holder for total cost in other accounts

        # Loop through accounts. Note that dayTotal is listed in displayList
        for accountNum in reportCostDict_input[reportDate]:

            # Only add account if in displayList; add everything else in Others
            if accountNum in displayListMonthly:
                displayReportCostDict[reportDate].update(
                    {accountNum: reportCostDict_input[reportDate][accountNum]}
                )
            else:
                otherAccounts = otherAccounts + reportCostDict_input[reportDate][accountNum]['Cost']

        # Enter total for 'Others' in the dictionary
        displayReportCostDict[reportDate].update({'Others': {'Cost': otherAccounts}})

    return displayReportCostDict


#--------------------------------------------------------------------------------------------------
# Process percentage changes for the reporting period

def process_percentchanges_per_month(monthlyCostDict_input):
    period = len(MONTHLY_COST_DATES)
    i = 0

    while i < period:
        if i == 0:
            for month_key in monthlyCostDict_input:
                for account in monthlyCostDict_input[month_key]:
                    monthlyCostDict_input[month_key][account].update({'percentDelta': None})
        if i > 0:
            for month_key in monthlyCostDict_input:
                for account in monthlyCostDict_input[month_key]:
                    try:
                        percentDelta = 0.0
                        current_month_cost = monthlyCostDict_input[month_key][account]['Cost']
                        
                        # Subtract 1 from the current month's value to get the previous month's value
                        current_month_year = month_key.split('-')
                        previous_month_year = [str(int(current_month_year[0])), str(int(current_month_year[1]) - 1)]
                        previous_month_key = '-'.join(previous_month_year)
                        
                        if previous_month_key in monthlyCostDict_input and account in monthlyCostDict_input[previous_month_key]:
                            previous_month_cost = monthlyCostDict_input[previous_month_key][account]['Cost']
                            percentDelta = (current_month_cost / previous_month_cost - 1)
                        else:
                            previous_month_cost = 0.0  # Handle the case where the data is missing
                            percentDelta = None
                        
                        monthlyCostDict_input[month_key][account].update({'percentDelta': percentDelta})
                    except ZeroDivisionError:
                        print('ERROR: Division by Zero')
                        monthlyCostDict_input[month_key][account].update({'percentDelta': None})
        i += 1
    return monthlyCostDict_input

#--------------------------------------------------------------------------------------------------
# Compile HTML for E-mail Body

def create_report_html(emailDisplayDict_input, BODY_HTML):

    #text_out = ''

    # Function to create styles depending on percent change
    def evaluate_change(value):
        if value < -.15:
            text_out = "<td style='text-align: right; padding: 4px; color: Navy; font-weight: bold;'>{:.2%}</td>".format(value)
        elif -.15 <= value < -.10:
            text_out = "<td style='text-align: right; padding: 4px; color: Blue; font-weight: bold;'>{:.2%}</td>".format(value)
        elif -.10 <= value < -.05:
            text_out = "<td style='text-align: right; padding: 4px; color: DodgerBlue; font-weight: bold;'>{:.2%}</td>".format(value)
        elif -.05 <= value < -.02:
            text_out = "<td style='text-align: right; padding: 4px; color: DeepSkyBlue; font-weight: bold;'>{:.2%}</td>".format(value)
        elif -.02 <= value <= .02:
            text_out = "<td style='text-align: right; padding: 4px;'>{:.2%}</td>".format(value)
        elif .02 < value <= .05:
            text_out = "<td style='text-align: right; padding: 4px; color: Orange; font-weight: bold;'>{:.2%}</td>".format(value)
        elif .05 < value <= .10:
            text_out = "<td style='text-align: right; padding: 4px; color: DarkOrange; font-weight: bold;'>{:.2%}</td>".format(value)
        elif .10 < value <= .15:
            text_out = "<td style='text-align: right; padding: 4px; color: OrangeRed; font-weight: bold;'>{:.2%}</td>".format(value)
        elif value > .15:
            text_out = "<td style='text-align: right; padding: 4px; color: Red; font-weight: bold;'>{:.2%}</td>".format(value)
        else:
            text_out = "<td style='text-align: right; padding: 4px;'>{:.2%}</td>".format(value)

        return text_out

    # Function to color rows
    def row_color(i_row):
        if (i_row % 2) == 0:
            return "<tr style='background-color: WhiteSmoke;'>"
        else:
            return "<tr>"

    # The HTML body of the email.
    BODY_HTML = BODY_HTML + "<table border=1 style='border-collapse: collapse; \
                font-family: Arial, Calibri, Helvetica, sans-serif; font-size: 12px;'>"

    # Generate the header of the report/e-mail:

    BODY_HTML = BODY_HTML + '<tr style="background-color: SteelBlue;">' + "<td>&nbsp;</td>" # start row; blank space in the top left corner

    # AWS Account names as labels in the TOP/FIRST ROW
    for accountNum in displayListMonthly:
        if accountNum in accountDict:
            BODY_HTML = BODY_HTML + "<td colspan=2 style='text-align: center;'><b>" + accountDict[accountNum] + "</b></td>"
        elif accountNum == 'Others':
            BODY_HTML = BODY_HTML + "<td colspan=2 style='text-align: center;'><b>Others</b></td>"
        elif accountNum == 'monthTotal':
            BODY_HTML = BODY_HTML + "<td colspan=2 style='text-align: center;'><b>Total</b></td>"

    BODY_HTML = BODY_HTML + "</tr>\n" # end row

    BODY_HTML = BODY_HTML + '<tr style="background-color: LightSteelBlue;">' + "<td style='text-align: center; width: 80px;'>Date</td>" # start next row; Date label

    # AWS Account numbers in the SECOND ROW
    for accountNum in displayListMonthly:
        if accountNum in accountDict:
            BODY_HTML = BODY_HTML + "<td style='text-align: center; width: 95px;'>" \
                        + accountNum + "</td><td style='text-align: center;'>&Delta; %</td>"
        elif accountNum == 'Others':
            BODY_HTML = BODY_HTML + "<td style='text-align: center; width: 95px;'> \
                        Other Accounts</td><td style='text-align: center;'>&Delta; %</td>"
        elif accountNum == 'monthTotal':
            BODY_HTML = BODY_HTML + "<td style='text-align: center; width: 95px;'> \
                        All Accounts</td><td style='text-align: center;'>&Delta; %</td>"

    BODY_HTML = BODY_HTML + "</tr>\n" # end row

    # Generate the table contents for report/e-mail:

    i_row=0

    for reportDate in emailDisplayDict_input:

        # Use different style for the LAST ROW
        if reportDate == END_DATE or reportDate == YESTERDAY:
            BODY_HTML = BODY_HTML + row_color(i_row) + "<td style='text-align: center; color: Teal'><i>" + reportDate + "*</i></td>"

            for accountNum in displayListMonthly:
                BODY_HTML = BODY_HTML + "<td style='text-align: right; padding: 4px; color: Teal'> \
                            <i>$ {:,.2f}</i></td>".format(round(emailDisplayDict_input[reportDate][accountNum]['Cost'],2))

                if emailDisplayDict_input[reportDate][accountNum]['percentDelta'] == None:
                    BODY_HTML = BODY_HTML + "<td>&nbsp;</td>"
                else:
                    BODY_HTML = BODY_HTML + "<td style='text-align: right; padding: 4px; color: Teal'> \
                                <i>{:.2%}</i></td>".format(emailDisplayDict_input[reportDate][accountNum]['percentDelta'])

            BODY_HTML = BODY_HTML + "</tr>\n"

            continue

        #BODY_HTML = BODY_HTML + "<!-- Start of Report Date " + reportDate + " -->\n"
        BODY_HTML = BODY_HTML + row_color(i_row) + "<td style='text-align: center;'>" + reportDate + "</td>"

        # Use normal format for MIDDLE ROWS
        for accountNum in displayListMonthly:
            BODY_HTML = BODY_HTML + "<td style='text-align: right; padding: 4px;'> \
                        $ {:,.2f}</td>".format(round(emailDisplayDict_input[reportDate][accountNum]['Cost'],2))

            if emailDisplayDict_input[reportDate][accountNum]['percentDelta'] == None:
                BODY_HTML = BODY_HTML + "<td>&nbsp;</td>"
            else:
                BODY_HTML = BODY_HTML + evaluate_change(emailDisplayDict_input[reportDate][accountNum]['percentDelta'])
                #BODY_HTML = BODY_HTML + "<td style='text-align: right; padding: 4px'> \
                #            {:.2%}</td>".format(emailDisplayDict_input[reportDate][accountNum]['percentDelta'])

        BODY_HTML = BODY_HTML + "</tr>\n"

        i_row += 1

    BODY_HTML = BODY_HTML + "</table><br>\n"

    #print(BODY_HTML)

    # * Note that total costs for this date are not reflected on this report.
    BODY_HTML = BODY_HTML + "<div style='color: Teal; font-size: 12px; font-style: italic;'> \
                * Note that total costs for this date are not reflected on this report.</div>\n"

    return BODY_HTML
    #return None

# =================================================================================================

#--------------------------------------------------------------------------------------------------
# Get Linked Account Dimension values from Master Payer Cost Explorer

def get_linked_accounts(accountList):

  results = []	# holder for full linked account results
  token = None	# holder for NextPageToken

  while True:

    if token:
      kwargs = {'NextPageToken': token}   # get the NextPageToken
    else:
      kwargs = {} # empty if the NextPageToken does not exist

    linked_accounts = cost_explorer.get_dimension_values(

            # Get all linked account numbers in the time period requested
            TimePeriod={'Start': START_DATE, 'End': END_DATE},
            Dimension='LINKED_ACCOUNT',
            **kwargs
        )

    # Save results - active accounts in time period
    results += linked_accounts['DimensionValues']

    token = linked_accounts.get('NextPageToken')
    if not token:
      break

    #print(results)

  active_accounts = []	# holder for just linked account numbers
  defined_accounts = []	# holder for reporting accounts

  for accountnumbers in results:
    #print(accountnumbers['Value'])
    active_accounts.append(accountnumbers['Value'])

  # use account number for report if it exists in dimension values
  for accountnumbers in accountList:
    if accountnumbers in active_accounts:
      defined_accounts.append(accountnumbers)

  #print(defined_accounts)

  return defined_accounts


#--------------------------------------------------------------------------------------------------
# Get Cost Data from Master Payer Cost Explorer

def get_cost_data(account_numbers):

  results = []	# holder for service costs
  token = None	# holder for NextPageToken

  while True:

    if token:
      kwargs = {'NextPageToken': token}   # get the NextPageToken

    else:
      kwargs = {} # empty if the NextPageToken doesn' exist

    data = cost_explorer.get_cost_and_usage(

      # Monthly cost and grouped by Account and Service
      TimePeriod={'Start': MONTHLY_START_DATE, 'End': MONTHLY_END_DATE},
      Granularity='MONTHLY',
      Metrics=['UnblendedCost'],
      GroupBy=[
        {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'},
        {'Type': 'DIMENSION', 'Key': 'SERVICE'}
      ],

      # Filter using active accounts listed in MEDaily Spend View
      Filter = {'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': account_numbers}},
      **kwargs)

    results += data['ResultsByTime']
    #print(data['ResultsByTime'])

    token = data.get('NextPageToken')
    if not token:
      break

    #print(results)

  return results


#--------------------------------------------------------------------------------------------------

def restructure_cost_data(cost_data_Dict, account_numbers):

  display_cost_data_Dict = {}             # holder for restructured dictionary for e-mail/display
  sorted_display_cost_data_Dict = {}      # holder for sorted dictionary for e-mail/display

  # use account numbers as main dictionary keys
  for account in account_numbers:
    display_cost_data_Dict.update({account: {}})

  # use service names as second dictionary keys
  for timeperiods in cost_data_Dict:
    #print(timeperiods)

    for cost in timeperiods['Groups']:
      #print(cost)
      account_no = cost['Keys'][0]		# Account Number
      account_name = cost['Keys'][1]		# Service Name

      #print(account_no + " " + account_name)
      try:
        display_cost_data_Dict[account_no].update({account_name: {}})
      except:
        continue

  # for each service, save costs per period
  for timeperiods in cost_data_Dict:
    #print(timeperiods)
    date = timeperiods['TimePeriod']['Start']

    for cost in timeperiods['Groups']:
      #print(cost)
      account_no = cost['Keys'][0]							# Account Number
      account_name = cost['Keys'][1]							# Service Name
      amount = cost['Metrics']['UnblendedCost']['Amount']		# Period Cost

      #print(account_no + " " + account_name)
      try:
        display_cost_data_Dict[account_no][account_name].update({date: amount})
      except:
        continue

    # sort the dictionary (per service) for each account
  for accounts in display_cost_data_Dict:
      #print(accounts)
      sorted_display_cost_data_Dict.update({accounts:{}})
      sorted_display_cost_data_Dict[accounts].update(sorted(display_cost_data_Dict[accounts].items()))
  
  #return display_cost_data_Dict
  return sorted_display_cost_data_Dict


#--------------------------------------------------------------------------------------------------
# Generate Table HTML Codes for e-mail formatting

def generate_html_table(cost_data_Dict, display_cost_data_Dict):

    # Function to create styles depending on percent change
  def evaluate_change(value):
    if value < -.15:
      text_out = "<td style='text-align: right; padding: 4px; color: Navy; font-weight: bold;'>{:.2%}</td>".format(value)
    elif -.15 <= value < -.10:
      text_out = "<td style='text-align: right; padding: 4px; color: Blue; font-weight: bold;'>{:.2%}</td>".format(value)
    elif -.10 <= value < -.05:
      text_out = "<td style='text-align: right; padding: 4px; color: DodgerBlue; font-weight: bold;'>{:.2%}</td>".format(value)
    elif -.05 <= value < -.02:
      text_out = "<td style='text-align: right; padding: 4px; color: DeepSkyBlue; font-weight: bold;'>{:.2%}</td>".format(value)
    elif -.02 <= value <= .02:
      text_out = "<td style='text-align: right; padding: 4px;'>{:.2%}</td>".format(value)
    elif .02 < value <= .05:
      text_out = "<td style='text-align: right; padding: 4px; color: Orange; font-weight: bold;'>{:.2%}</td>".format(value)
    elif .05 < value <= .10:
      text_out = "<td style='text-align: right; padding: 4px; color: DarkOrange; font-weight: bold;'>{:.2%}</td>".format(value)
    elif .10 < value <= .15:
      text_out = "<td style='text-align: right; padding: 4px; color: OrangeRed; font-weight: bold;'>{:.2%}</td>".format(value)
    elif value > .15:
      text_out = "<td style='text-align: right; padding: 4px; color: Red; font-weight: bold;'>{:.2%}</td>".format(value)
    else:
      text_out = "<td style='text-align: right; padding: 4px;'>{:.2%}</td>".format(value)

    return text_out

    # Function to color rows
  def row_color(i_row):
    if (i_row % 2) == 0:
      return "<tr style='background-color: WhiteSmoke;'>"
    else:
      return "<tr>"


  # Start HTML table
  emailHTML = '<h2>AWS Monthly Cost Report for BPaaS Accounts - Per Service Breakdown</h2>' + \
        '<table border="1" style="border-collapse: collapse;">'

  for accounts in display_cost_data_Dict:
    #print(accounts)

    # table headers
    emailHTML = emailHTML + '<tr style="background-color: SteelBlue;">' + \
          '<td colspan="' + str(COLUMNS) + '" style="text-align: center; font-weight: bold">' + \
                    accountDict[accounts] + ' (' + accounts + ')</td></tr>'
          #accountDict[accounts] + ' - ' + accounts + ' | ' + accountMailDict[accounts] + '</td></tr>'
    emailHTML = emailHTML + '<tr style="background-color: LightSteelBlue;">' + \
          '<td style="text-align: center; font-weight: bold">Service Name</td>'

    # timeperiod headers
    for timeperiods in cost_data_Dict:

      if timeperiods['TimePeriod']['Start'] != START_DATE:
        emailHTML = emailHTML + '<td style="text-align: center;">&Delta; %</td>'

      emailHTML = emailHTML + '<td style="text-align: center; font-weight: bold">' + timeperiods['TimePeriod']['Start']
      
      if timeperiods['TimePeriod']['Start'] == END_DATE or timeperiods['TimePeriod']['Start'] == YESTERDAY:
          emailHTML = emailHTML + '*'
      
      emailHTML = emailHTML + '</td>'
      

    emailHTML = emailHTML + '</tr>'

    i_row = 0	# row counter for tracking row background color

      # services and costs per timeperiod
    for service in display_cost_data_Dict[accounts]:

      rsrcrowHTML = ''		# Resource row HTML code
      tdcostvalues = []		# List of <td> cost values for tracking zeros

      # Based on service (Refund or Tax) or row count, pick a background color
      if service == 'Refund' or service == 'Tax':
        rsrcrowHTML = rsrcrowHTML + '<tr style="font-style: italic; background-color: Linen;">'
      else:
        rsrcrowHTML = rsrcrowHTML + row_color(i_row)

      # Leading the row with Service Name
      rsrcrowHTML = rsrcrowHTML + '<td style="text-align: left;">' + service + '</td>'

      prevdaycost = None	# previous month cost
      currdaycost = 0.0	# current month cost
      pctfrmprev = 0.0	# percentage delta from previous to curent day

      for timeperiods in cost_data_Dict:
        date = timeperiods['TimePeriod']['Start']

        # Calculate delta(s) after the first month <td>
        if prevdaycost is not None:

          try:
            currdaycost = round(float(display_cost_data_Dict[accounts][service][date]),2)
          except:
            currdaycost = 0

          # Calculate % if previous and current costs are not zero
          if prevdaycost != 0 and currdaycost != 0:
            pctfrmprev = (currdaycost / prevdaycost) - 1
            rsrcrowHTML = rsrcrowHTML + evaluate_change(pctfrmprev)
          else:
            rsrcrowHTML = rsrcrowHTML + '<td>&nbsp;</td>'

        try:
          cost_td = round(float(display_cost_data_Dict[accounts][service][date]),2)
          prevdaycost = (round(float(display_cost_data_Dict[accounts][service][date]),2))
        except:
          cost_td = 0
          prevdaycost = 0

        rsrcrowHTML = rsrcrowHTML + '<td style="text-align: right; padding: 4px;">'
        rsrcrowHTML = rsrcrowHTML + "$ {:,.2f}".format(cost_td) + '</td>'
        tdcostvalues.append("$ {:,.2f}".format(cost_td))

      rsrcrowHTML = rsrcrowHTML + '</tr>'

      # Check if all cost values in the row are the same
      allSame = False;
      if len(tdcostvalues) > 0:
        allSame = all(elem == tdcostvalues[0] for elem in tdcostvalues)

      # If all values are zero, skip row
      if allSame:
        if tdcostvalues[0] == "$ 0.00":
          continue

      emailHTML = emailHTML + rsrcrowHTML		# Include row for displaying
      i_row += 1								# row counter

  emailHTML = emailHTML + '</table>'

  return emailHTML

# =================================================================================================

#--------------------------------------------------------------------------------------------------
# Compile and send HTML E-mail

def send_report_email(BODY_HTML):

    SENDER = os.environ['SENDER']
    RECIPIENT = os.environ['RECIPIENT']
    RECIPIENT2 = os.environ['RECIPIENT2']
    RECIPIENT3 = os.environ['RECIPIENT3']
    RECIPIENT4 = os.environ['RECIPIENT4']
    RECIPIENT5 = os.environ['RECIPIENT5']
    RECIPIENT6 = os.environ['RECIPIENT6']
    RECIPIENT7 = os.environ['RECIPIENT7']
    RECIPIENT8 = os.environ['RECIPIENT8']
    RECIPIENT9 = os.environ['RECIPIENT9']
    RECIPIENT10 = os.environ['RECIPIENT10']
    AWS_REGION = os.environ['AWS_REGION']
    SUBJECT = "AWS Monthly Cost Report for BPaaS Accounts"

    # The email body for recipientients with non-HTML email clients.
    BODY_TEXT = ("Amazon SES\r\n"
                "An HTML email was sent to this address."
                )

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)

    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                    RECIPIENT2,
                    RECIPIENT3,
                    RECIPIENT4,
                    RECIPIENT5,
                    RECIPIENT6,
                    RECIPIENT7,
                    RECIPIENT8,
                    RECIPIENT9,
                    RECIPIENT10
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,

        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


#--------------------------------------------------------------------------------------------------
# Lambda Handler

def lambda_handler(context=None, event=None):

    # Using dictionary of 23 named accounts, get cost info from Cost Explorer
    # Result is dictionary keyed by account number
    mainCostDict = ce_get_costinfo_per_account(accountDict)

    print(mainCostDict)

    # Re-sort the mainCostDict; create a new dictionary keyed by reporting date
    mainDailyDict = process_costchanges_per_month(mainCostDict)

    print(mainDailyDict)

    # Create a new dictionary (from mainDailyDict) with only big cost accounts labeled
    # Combine other accounts into "Others"
    mainDisplayDict = process_costchanges_for_display(mainDailyDict)

    print(mainDisplayDict)

    # Update mainDisplayDict dictionary to include daily percent changes
    finalDisplayDict = process_percentchanges_per_month(mainDisplayDict)

    print(finalDisplayDict)

    # Generate HTML code using finalDisplayDict and send HTML e-mail
    summary_html = create_report_html(finalDisplayDict, BODY_HTML)


    # =============================================================================================

    account_numbers = get_linked_accounts(accountList)

    print(account_numbers)

    # Get cost data from the Master Payer Account
    cost_data_Dict = get_cost_data(account_numbers)

    print(cost_data_Dict)

    # Restruction dictionary for email message display
    display_cost_data_Dict = restructure_cost_data(cost_data_Dict, account_numbers)

    print(display_cost_data_Dict)

    # Put the restructured dictionary in HTML table
    html_for_email = generate_html_table(cost_data_Dict, display_cost_data_Dict)

    html_for_email = summary_html + '<br><br>' + html_for_email

    # Send HTML e-mail
    send_report_email(html_for_email)

