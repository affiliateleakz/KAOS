"""Parse SEC 13F information-table XML into quarterly holdings, never transactions."""
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

def parse_13f_information_table(xml_text):
    if len(xml_text)>5_000_000 or "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise ValueError("Unsafe or oversized 13F XML")
    try: root=ET.fromstring(xml_text)
    except ET.ParseError as exc: raise ValueError("Malformed 13F XML") from exc
    def local(tag): return tag.split("}")[-1].lower()
    if local(root.tag) not in ("informationtable", "form13finformationtable"):
        raise ValueError("Not a 13F information table")
    rows=[]
    for info in root:
        if local(info.tag)!="infotable":continue
        fields={}
        def collect(el):
            children=list(el)
            if not children:fields[local(el.tag)]=(el.text or "").strip()
            else:
                for child in children:collect(child)
        collect(info)
        issuer=fields.get("nameofissuer","")
        cusip=fields.get("cusip","")
        value=fields.get("value","")
        shares=fields.get("sshprnamt","")
        if not issuer or not cusip or not value:continue
        try:
            reported=Decimal(value)
            units=Decimal(shares) if shares else None
            if reported<0 or (units is not None and units<0):raise ValueError("Negative 13F quantities")
        except InvalidOperation as exc:raise ValueError("Invalid 13F value or quantity") from exc
        rows.append({"issuer":issuer,"cusip":cusip,"title_class":fields.get("titleofclass",""),
                     "reported_value_thousands_usd":str(reported),
                     "reported_shares_or_principal":str(units) if units is not None else None,
                     "share_type":fields.get("sshprnamttype"),
                     "action":"holding","ticker":None})
    return rows
