import boto3
import argparse
import login

def get_user(active_session,email):
    try:
        sso_client = active_session.client('identitystore', region_name='eu-west-1')
        response = sso_client.list_users(
          IdentityStoreId='INSERT HERE YOUR ID',
          Filters=[
            {
                'AttributePath': 'UserName',
                'AttributeValue': email
            },
        ]
        )
        return(response["Users"][0]["UserId"])



    except Exception as err:
        template = "An exception of type {0} occurred. Arguments:\n{1!r} "
        message = template.format(type(err).__name__, err.args)
        print(message)





def main():
    # parse user arguments
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--aws_access_key", required=True, type=str, help="AWS Access Key")
    parser.add_argument("--aws_secret_key", required=True, type=str, help="AWS Secret Key")
    parser.add_argument("--email", required=True, type=str, help="Email")
    args = parser.parse_args()
    this_session = login.login(args.aws_access_key, args.aws_secret_key)
    user_id=get_user(this_session,args.email)
    org_client = boto3.client('organizations',aws_access_key_id=args.aws_access_key,aws_secret_access_key=args.aws_secret_key)
    sso_client = this_session.client('identitystore', region_name='eu-west-1')
    admin_client = this_session.client('sso-admin', region_name='eu-west-1')
    groups = sso_client.list_group_memberships_for_member(
    IdentityStoreId='d-936714c5de',
    MemberId={
        'UserId': user_id
    },
    MaxResults=100,

    )
    
    listaccounts = org_client.list_accounts()
    accounts = listaccounts['Accounts']
    while 'NextToken' in listaccounts:
        listaccounts = org_client.list_accounts(NextToken=listaccounts['NextToken'])
        accounts.extend(listaccounts['Accounts'])
    listpermissionsets = admin_client.list_permission_sets(
        InstanceArn='INSERT ARN',
        MaxResults=100
    )
    arn = listpermissionsets['PermissionSets']
    for permission_set in arn:
        response = admin_client.describe_permission_set(
        InstanceArn='INSERT ARN',
        PermissionSetArn= permission_set
            )
        name = response['PermissionSet']['Name']
        for i in accounts:
            account_id= i['Id']
            account_name=i['Name']
            response1 = admin_client.list_account_assignments(
                AccountId=account_id,
                InstanceArn='INSERT ARN',
                MaxResults=100,
                PermissionSetArn=permission_set
            )
            for assignment in response1['AccountAssignments']:
                if assignment['PrincipalId'] == user_id:
                    print("Account Name:", account_name)
                    print("Account ID:", account_id)
                    print("Permission Set", name)
                    print("------------------")
                    #break
                else:
                    for membership in groups['GroupMemberships']:
                        group_id = membership['GroupId']
                        if assignment['PrincipalId'] == group_id:
                            groupname = sso_client.describe_group(
                            IdentityStoreId='INSERT ID',
                            GroupId=group_id
                            )
                            
                            display_name = groupname['DisplayName']

                            print("Account Name: ", account_name)
                            print("Account ID: ", account_id)
                            print("Permission Set: ", name)
                            print("Premission Set was Inherited from group: ", display_name)
                            print("------------------")


    

            #print(response1)
            #break
        #break
            



if __name__ == "__main__":
    main()
