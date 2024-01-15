import boto3
import datetime
from datetime import datetime
athena = boto3.client('athena')

current_year = datetime.now().strftime("%Y")
#print(current_year)
current_month = datetime.now().strftime("%m")
#current_day_number = datetime.now().strftime("%d")
#print(current_month)
def lambda_handler(event, context):
    query = """
    SELECT line_item_usage_type, line_item_operation, product_region, identity_time_interval, line_item_product_code, line_item_usage_account_id, line_item_unblended_cost, bill_billing_period_start_date, line_item_usage_start_date, line_item_usage_end_date, line_item_usage_amount, resource_tags_user_job_id,resource_tags_user_deployment_id,resource_tags_user_project, resource_tags_user_t_p_k_nickname,resource_tags_user_mx_branch, resource_tags_user_mx_usage, resource_tags_user_mx_version
    FROM cur_report_athena
    WHERE line_item_usage_account_id in ('ACCOUNT_ID_1', 'ACCOUNT_ID_2', 'ACCOUNT_ID_3') AND product_region = 'eu-west-1' AND line_item_line_item_type NOT IN ('Tax','Credit','Refund') AND bill_billing_period_start_date >= now() - INTERVAL '1' month AND line_item_unblended_cost > 0
    """
    
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': 'athenacurcfn_c_u_r_report_athena'
        },
        ResultConfiguration={
            'OutputLocation': f's3://BUCKET_NAME_HERE/FOLDER_NAME_HERE/{current_year}/{current_month}/'
        }
    )
