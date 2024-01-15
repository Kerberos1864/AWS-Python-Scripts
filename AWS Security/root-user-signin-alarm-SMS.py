import json
import boto3
import logging


def lambda_handler(event, context):
    # Initialize AWS services
    
    sns_client = boto3.client('sns', region_name='us-east-1')
 
    console_login_status = event.get('detail', {}).get('responseElements', {}).get('ConsoleLogin')
    sourceIPAddress = event.get('detail', {}).get('sourceIPAddress')
    print(sourceIPAddress)

    #Publish the truncated message to an SNS topic
    sns_topic_arn = 'arn:aws:sns:us-east-1:938039726974:AWS-Root-User-Activity'
    sns_client.publish(
        TopicArn=sns_topic_arn,
        #Message=f'Login Attempt: {console_login_status}',
        Message=f'Login Attempt: {console_login_status}\nSource IP Address: {sourceIPAddress}',
        Subject='AWS Root User Activity'
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Message sent successfully')
    }
