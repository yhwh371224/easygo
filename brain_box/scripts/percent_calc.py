def calc_percent_price(base_price, percent, trade_type="Long"):
    """
    Calculate final price based on percentage change.
    If trade_type is 'Short', the percentage is reversed.
    Supports full word or first letter: 'L', 'l', 'S', 's'
    """
    trade_type_clean = trade_type.strip().lower()
    if trade_type_clean.startswith("s"):  # Short
        percent = -percent
        trade_type_clean = "Short"
    else:  # Default to Long
        trade_type_clean = "Long"
    
    return base_price * (1 + percent / 100), trade_type_clean

if __name__ == "__main__":
    print("📊 Terminal Percentage Calculator")
    
    base_price = float(input("Enter base price: "))
    percent = float(input("Enter percentage (%): "))
    trade_type = input("Enter trade type (Long or Short, L/S): ")

    final_price, trade_type_display = calc_percent_price(base_price, percent, trade_type)
    print(f"\n💹 {trade_type_display} final price: {final_price:.4f}")

