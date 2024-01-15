import boto3
import datetime


def lambda_handler(event, context):
    # Create an AWS Organizations client
    org_client = boto3.client('organizations')
    ce = boto3.client('ce')
    ce1 = boto3.client('ce',region_name='eu-west-1')
    ses_client = boto3.client('ses')
    #below_email_to_receive_notifications
    cloud_admin_email = 'test@aws.com'
    owner_email=""
    end_date = datetime.date.today()
    print(end_date)
    notification_emails = []
    start_date = datetime.date.today() - datetime.timedelta(days=1)
    print(start_date)
    listaccounts = org_client.list_accounts()
    accounts = listaccounts['Accounts']
    while 'NextToken' in listaccounts:
        listaccounts = org_client.list_accounts(NextToken=listaccounts['NextToken'])
        accounts.extend(listaccounts['Accounts'])
    for i in accounts:
        notification_emails = []
        account_name=i['Name']
        account_id=i['Id']
        response_tags = org_client.list_tags_for_resource(
                    ResourceId=i['Id'],
                    )
        tags = response_tags['Tags']
        specific_tag_value = None
        for tag in tags:
            if tag['Key']=='Owner Name':
                owner_name=tag['Value']
            elif tag['Key'] == 'Owner Email':
                owner_email = tag['Value']
            elif tag['Key'] == 'Threshold':
                threshold = tag['Value']
            elif tag['Key']=='Notification Emails':
                notification_emails=tag['Value'].split()
                break
        print(account_name)
        print(account_id)
        print(owner_name)
        print(owner_email)
        cc_emails= [cloud_admin_email]
        cc_emails.extend(notification_emails)
    
    # Get the daily cost and usage for account ID 1234567890.
        try:
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                Filter={
            'And': [
                {
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [account_id],
                        'MatchOptions': [
                            'EQUALS'
                        ]
                    }
                },
                {
                    'Dimensions': {
                        'Key': 'RECORD_TYPE',
                        'Values': ['Usage'], 
                        'MatchOptions': [
                            'EQUALS'
                            ]
                        }
                    }
                ]
            }
            )
            
            responser = ce1.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                Filter={
            'And': [
                {
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [account_id],
                        'MatchOptions': [
                            'EQUALS'
                        ]
                    }
                },
                {
                    'Dimensions': {
                        'Key': 'RECORD_TYPE',
                        'Values': ['Usage'], 
                        'MatchOptions': [
                            'EQUALS'
                            ]
                        }
                    },
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ["Amazon Elastic Compute Cloud - Compute"], 
                        'MatchOptions': [
                            'EQUALS'
                            ]
                        }
                    }
                ]
            }
            )
            
            ec = responser['ResultsByTime'][0]['Total']['BlendedCost']['Amount']
            ec_float = float(ec)
            ec2_amount = f"{ec_float:.2f}"

            print(f"EC2 cost: {ec2_amount}")
            
            
            responsec = ce1.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                Filter={
            'And': [
                {
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [account_id],
                        'MatchOptions': [
                            'EQUALS'
                        ]
                    }
                },
                {
                    'Dimensions': {
                        'Key': 'RECORD_TYPE',
                        'Values': ['Usage'], 
                        'MatchOptions': [
                            'EQUALS'
                            ]
                        }
                    },
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ["Amazon Relational Database Service"], 
                        'MatchOptions': [
                            'EQUALS'
                            ]
                        }
                    }
                ]
            }
            )
            rd = responsec['ResultsByTime'][0]['Total']['BlendedCost']['Amount']
            rds_float=float(rd)
            rds_amount = f"{rds_float:.2f}"
            print(f"RDS cost: {rds_amount}")
        
            co = response['ResultsByTime'][0]['Total']['BlendedCost']['Amount']
            co_float=float(co)
            cost_amount = f"{co_float:.2f}"
            
            print(cost_amount)
            daily_cost=int(float(cost_amount))
            print(daily_cost)
            limit=int(threshold)
            
            if daily_cost >= limit:
                owners=owner_email.split()
                ses_client.send_templated_email(
                Source='ENTER YOUR SOURCE EMAIL HERE SES',
                Destination={
                    'ToAddresses': owners,
                    'CcAddresses': cc_emails,
                },
                Template='Billing-Alarm-Template',
                TemplateData='{\"AccountName\": \"'+account_name+'\",\"AccountId\": \"'+account_id+'\",\"Name\": \"'+owner_name+'\",\"Threshold\": \"'+threshold+'\",\"EstimatedCharges\": \"'+cost_amount+'\",\"rds_amount\": \"'+rds_amount+'\",\"ec2_amount\": \"'+ec2_amount+'\"}'
                )
                time.sleep(1)
            
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        

 
