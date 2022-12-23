import math
from difflib import SequenceMatcher
import json

import requests
import fitz


def get_postal(session:requests.Session, code:str):
    """
    B2クラウドの郵便番号情報を取得する

    Args:
        session(requests.Session): ログイン済みのセッション
        code(str):郵便番号7桁

    Returns:
        郵便番号情報
    """
    url = 'https://newb2web.kuronekoyamato.co.jp/b2/p/_postal'
    params = {'code':code}
    response = session.get(url, params=params)
    return json.loads(response.text)


def create_dm_shipment(
    shipment_date:str,
    consignee_telephone_display:str,
    consignee_name:str,
    consignee_zip_code:str,
    consignee_address1:str,
    consignee_address2:str,
    consignee_address3:str,
    consignee_address4:str = '',
    consignee_department1:str = '',
    consignee_department2:str = '',
    shipment_number:str = '',
    consignee_title:str = '',
    consignee_name_kana:str = '',
    consignee_code:str = '',
    is_using_center_service:str = '0',
    consignee_center_code:str = '',
    consignee_center_name:str = ''
):
    """
    DM伝票用のデータを生成する

    Args:
        shipment_date: 発送日
        consignee_telephone_display: 電話番号
        consignee_name:お客様名
        consignee_zip_code:郵便番号
        consignee_address1:都道府県名
        consignee_address2:市区
        consignee_address3:町名・番地
        consignee_address4:ビル・マンション名
        consignee_department1:会社・部門1
        consignee_department2:会社・部門2
        shipment_number:お客様管理番号
        consignee_title:敬称
        consignee_name_kana:略称ｶﾅ（半角）
        consignee_code:お届け先コード
        is_using_center_service:営業所止置きサービスを利用する "0":しない, "1":する
        consignee_center_code:営業所コード
        consignee_center_name:営業所名
    """
    shipment = locals()
    shipment['service_type'] = '3'
    return {'shipment':shipment}


def create_empty_shipment():
    """
    空のshipmentを生成する
    """
    return {
        "shipment": {
            "tracking_number": "",
            "shipment_number": "",
            "service_type": "",# 必須 0:発払い,3:ＤＭ便,4:タイム,5:着払い,7:ネコポス,8:宅急便コンパクト
            "is_cool": "",
            "shipment_date": "",# 必須
            "delivery_date": "",
            "amount": "",
            "tax_amount": "",
            "is_printing_lot": "",
            "invoice_code": "",# 必須 (発払い)
            "invoice_code_ext": "",
            "invoice_freight_no": "", # 必須 (発払い)
            "invoice_name": "",
            "payment_flg": "",
            "payment_number": "",
            "payment_receipt_no1": "",
            "payment_receipt_no2": "",
            "payment_receipt_no3": "",
            "closure_key": "",
            "search_key_title1": "",
            "search_key1": "",
            "search_key_title2": "",
            "search_key2": "",
            "search_key_title3": "",
            "search_key3": "",
            "search_key_title4": "",
            "search_key4": "",
            "search_key_title5": "",
            "search_key5": "",
            "sorting_code": "",
            "sorting_ab": "",
            "is_printing_date": "",
            "package_qty": "",
            "delivery_time_zone": "",
            "is_using_shipment_email": "",
            "shipment_email_address": "",
            "input_device_type": "",
            "shipment_message": "",
            "is_using_delivery_email": "",
            "delivery_email_address": "",
            "delivery_message": "",
            "shipper_code": "",
            "shipper_telephone": "",
            "shipper_telephone_display": "",
            "shipper_telephone_ext": "",
            "shipper_name": "",
            "shipper_title": "",
            "shipper_zip_code": "",
            "shipper_address": "",
            "shipper_address1": "",
            "shipper_address2": "",
            "shipper_address3": "",
            "shipper_address4": "",
            "shipper_name_kana": "",
            "consignee_code": "",
            "consignee_telephone": "",
            "consignee_telephone_display": "",# 必須
            "consignee_telephone_ext": "",
            "consignee_name": "",# 必須
            "consignee_zip_code": "",# 必須
            "consignee_address": "",
            "consignee_address1": "",# 必須
            "consignee_address2": "",# 必須
            "consignee_address3": "",
            "consignee_address4": "",
            "consignee_department1": "",
            "consignee_department2": "",
            "consignee_name_kana": "",
            "consignee_title": "",
            "is_using_center_service": "",
            "consignee_center_code": "",
            "consignee_center_name": "",
            "item_code1": "",
            "item_code2": "",
            "item_name1": "",# 必須 (DM以外)
            "item_name2": "",
            "handling_information1": "",
            "handling_information2": "",
            "note": "",
            "shipment_flg": "",
            "checked_date": "",
            "is_using_shipment_post_email": "",
            "shipment_post_email_address": "",
            "shipment_post_input_device_type": "",
            "shipment_post_message": "",
            "is_using_cons_deli_post_email": "",
            "cons_deli_post_email_address": "",
            "cons_deli_post_input_device_type": "",
            "cons_deli_post_message": "",
            "is_using_shipper_deli_post_email": "",
            "shipper_deli_post_email_address": "",
            "shipper_deli_post_input_device_type": "",
            "shipper_deli_post_message": "",
            "display_flg": "",
            "reissue_count": "",
            "is_printing_logout": "",
            "error_flg": "",
            "is_agent": "",
            "cooperation_number": "",
            "notification_email_address": "",
            "direct_delivery_type": ""
        }
    }


def split_pdf_dm(pdf_data:bytes, length:int):
    """
    DMの伝票pdfデータを伝票毎に分割する

    Args:
        pdf_data:DMのPDFデータ
        length:分割数

    Returns:
        list[bytes]: 分割されたPDFデータ
    """
    ret = []
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    for i in range(length):
        # 対応する伝票のページ、列、行を算出
        page_num = math.floor(i / 8)
        row_num = math.floor((i % 8) / 2)
        col_num = i % 2
        page = doc[page_num]

        # 250x200のboxで切り抜く
        rect = fitz.Rect(
            50 + 250 * col_num,
            30 + 204 * row_num,
            50 + 250 * col_num + 250,
            30 + 204 * row_num + 200)
        page.set_cropbox(rect)
        _doc = fitz.open()
        _doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        ret.append(_doc.tobytes())
    return ret


def split_pdf_nekopos(pdf_data:bytes, length:int):
    """
    ネコポスの伝票pdfデータを伝票毎に分割する

    Args:
        pdf_data:DMのPDFデータ
        length:分割数

    Returns:
        list[bytes]: 分割されたPDFデータ
    """
    ret = []
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    for i in range(length):
        # 対応する伝票のページ、列、行を算出
        page_num = math.floor(i / 6)
        row_num = math.floor((i % 6) / 2)
        col_num = i % 2
        page = doc[page_num]

        # 250x200のboxで切り抜く
        rect = fitz.Rect(
            20 + 272 * col_num,
            35 + 263 * row_num,
            20 + 272 * col_num + 265,
            35 + 263 * row_num + 255)
        page.set_cropbox(rect)
        _doc = fitz.open()
        _doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        ret.append(_doc.tobytes())
    return ret


def choice_postal(postal_feed:dict, address:str):
    """
    郵便番号の複数の住所情報から最適な情報を取得する

    Args:
        postal_feed(dict): get_postalで取得した郵便番号情報
        address: マッチングさせる住所
    """
    ret = None
    max_ratio = 0
    for postal in postal_feed['feed']['entry']:
        _address = postal['address']['address1'] + postal['address']['address2'] + postal['address']['address3']
        ratio = SequenceMatcher(None, address, _address).ratio()
        if ratio > max_ratio:
            max_ratio = ratio
            ret = postal
    return ret


def get_address_info(session:requests.Session, addressian_api_key:str, address:str, zip_code=None, prefix='consignee'):
    """
    住所情報を取得する

    Args:
        session:
        addressian_api_key: addressianのapi_key
        address: 変換対象の住所
        zip_code:郵便番号7桁 zip_codeを強制します。
        prefix: 戻り値につける接頭文字 consignee, shipper等

    Returns:
        dict: 住所情報
        {
            '{prefix}_zip_code': 郵便番号,
            '{prefix}_address1': 都道府県,
            '{prefix}_address2': 市区,
            '{prefix}_address3': 町村+番地,
            '{prefix}_address4': ビル・マンション等
        }
    """
    params = {
        'key':addressian_api_key,
        'address':address,
        'format':'json'
    }
    res_json = requests.get(f'https://s32y6jl1f8.execute-api.ap-northeast-1.amazonaws.com/api/address_normalizer', params=params).json()
    if res_json.get('message') is not None:
        raise Exception(f'addressianエラー:{res_json}')
    normalized = res_json['items'][0]
    # 住所が不明な場合は例外で終了
    if normalized['success'] == False:
        raise Exception(f'addressianエラー:不明な住所です.{address}')
    # 郵便番号が指定されている場合は、優先する（事業所専用の郵便番号等）
    if zip_code is None:
        zip_code = normalized['zip_code']
    # b2クラウドの郵便番号情報を取得する
    postal_feed = get_postal(session, zip_code)
    # 住所と最も一致度の高い郵便情報を選択する
    postal = choice_postal(postal_feed, address)
    # 住所情報を組み立てて、戻す
    return {
        f'{prefix}_zip_code': postal['address']['zip_code'],
        f'{prefix}_address1': postal['address']['address1'],
        f'{prefix}_address2': postal['address']['address2'],
        f'{prefix}_address3': normalized['town_type2'] + normalized['custom_type2'],
        f'{prefix}_address4': normalized['building']
    }