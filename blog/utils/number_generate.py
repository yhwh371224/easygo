import re


def generate_settlement_number(driver, date, seq):
    """
    Build a settlement number like SYD-MANSOOR-260601-SET-01.

    Args:
        driver: Driver instance — must have region.primary_airport set.
        date:   The settlement to_date (period-end date).
        seq:    Integer sequence for same-driver same-period settlements (1-based).

    Raises:
        ValueError if the driver's region or primary_airport is not configured.
    """
    if not driver.region:
        raise ValueError(
            f"Driver '{driver.driver_name}' has no region set — "
            "cannot generate a settlement number."
        )
    if not driver.region.primary_airport:
        raise ValueError(
            f"Driver '{driver.driver_name}' region '{driver.region}' has no "
            "primary_airport set — cannot generate a settlement number."
        )

    region = driver.region.primary_airport.code.upper()

    raw_first = (driver.driver_name or '').split()[0] if driver.driver_name else ''
    name = re.sub(r'[^A-Z0-9]', '', raw_first.upper()) or 'DRIVER'

    yymmdd = date.strftime("%y%m%d")

    return f"{region}-{name}-{yymmdd}-SET-{seq:02d}"
