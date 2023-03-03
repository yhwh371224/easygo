from twilio.rest import Client


def sms_single(request):
    account_sid = 'AC9ad86a3cd3fc22fa11c35d8d17bde7a0'
    auth_token = '632142d0e5afac3e05359e87abe61d2a'

    client = Client(account_sid, auth_token)

    def sms_one(sendto):
        client.messages.create(body="EasyGo - Just reminder of your booking \
                                        \nYour booking is coming on   \
                                        \nPickup time:  \
                                        \nEasyGo airport \
                                        \n\nAny changes? please let us know\
                                        \nDoNotReply>ToThisNumber\
                                        \nInstead,>> https://easygotransport.com/contact",
                               from_='+61488885330',
                               to=sendto)

    sms_one('')
