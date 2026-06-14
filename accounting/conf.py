from datetime import date

# The date EasyGo's GST registration became effective (cash basis).
# Every Post whose pickup_date falls on or after this date is treated as
# a taxable supply — paid ÷ 11 = GST collected (1A).
#
# TODO: replace with the actual ATO-confirmed registration date before
#       generating the first BAS.
GST_REGISTRATION_DATE = date(2025, 7, 1)
