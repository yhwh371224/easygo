def generate_settlement_number(driver, date, seq):
    region = driver.region.code  # SYD
    name = driver.code           # JSMITH
    yymmdd = date.strftime("%y%m%d")

    return f"{region}-{name}-{yymmdd}-SET-{seq:02d}"