import boto3
import json
import os
import pandas as pd
from botocore.handlers import disable_signing
from datetime import datetime

TABLE_NAME = os.environ.get("TABLENAME")
OUTPUT_BUCKET = os.environ.get("BUCKETNAME")
TEMP_FILENAME = f"/tmp/-{datetime.now():%Y-%b-%d %H:%M}.csv"
OUTPUT_KEY = f"NAME-{datetime.now():%Y-%b-%d %H:%M}.csv"

s3_resource = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table("TABLENAME")


def lambda_handler(event, context):
    response = table.scan()
    df = pd.DataFrame(response['Items'])
    df.to_csv(TEMP_FILENAME, index=False, header=True)

    # Upload temp file to S3
    #s3_resource.Bucket(OUTPUT_BUCKET).upload_file(TEMP_FILENAME, OUTPUT_KEY)
    s3_resource.meta.client.upload_file(TEMP_FILENAME, 'dynamobackups3', OUTPUT_KEY)
    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
            "content-type": "application/json"
        },
        'body': json.dumps('OK')
    }
