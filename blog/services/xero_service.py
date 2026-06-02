def export_settlement_to_xero(settlement):
    """
    Export a single settlement to Xero as a Bill (ACCPAY).

    Guard: settlement.status must be 'paid' before calling.

    On success will set settlement.xero_exported=True, xero_exported_at,
    xero_invoice_id, and xero_reference, then save the settlement.
    """
    raise NotImplementedError("Xero export not yet implemented.")


def export_settlements_for_period(from_date, to_date):
    """
    Monthly batch export: gathers all settlements with status='paid'
    whose settled_at falls within [from_date, to_date] and exports each
    via export_settlement_to_xero().
    """
    raise NotImplementedError("Xero batch export not yet implemented.")
