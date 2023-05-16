import b2cloud
import b2cloud.utilities
import time
from datetime import datetime
session = None

def test_login(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    ログイン
    """
    global session
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)


def test_get_postal(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    郵便情報
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.utilities.get_postal(session, '8950012')
    assert res == {'feed': {'entry': [{'address': {'address1_code': '46', 'address2_code': '215', 'address1': '鹿児島県', 'address2': '薩摩川内市', 'zip_code': '8950012', 'address3': '平佐'}}, {'address': {'address1_code': '46', 'address2_code': '215', 'address1': '鹿児島県', 'address2': '薩摩川内市', 'zip_code': '8950012', 'address3': '平佐町'}}]}}


def test_get_history(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    伝票発行履歴の取得
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.get_history(session, params={'all':''})
    for entry in res['feed']:
        assert 'title' not in entry


def test_get_history_all(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    全ての伝票発行履歴の取得
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.get_history_all(session)
    for entry in res['feed']:
        assert 'title' not in entry


def test_search_history(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    伝票発行履歴の検索
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.search_history(session, service_type='3')
    for entry in res['feed']:
        assert 'title' not in entry


def test_check_shipment(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    伝票情報のチェック
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    shipment = b2cloud.utilities.create_dm_shipment(
        datetime.now().strftime('%Y/%m/%d'),
        "00-0000-0000",
        "テスト",
        "8900053",
        "鹿児島県",
        "鹿児島市",
        "中央町10",
        consignee_name_kana="ｲﾝﾀｰﾏﾝ",
        is_using_center_service="0",
        consignee_center_code=""
    )
    res = b2cloud.check_shipment(session, shipment)
    assert res == {'success': True, 'errors': []}


def test_check_shipment_fault(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    伝票情報のチェック（データに不備ありの場合）
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    shipment = b2cloud.utilities.create_dm_shipment(
        datetime.now().strftime('%Y/%m/%d'),
        "00-0000-0000",
        "テスト",
        "8950012",
        "鹿児島県",
        "鹿児島市",
        "中央町10",
        consignee_name_kana="ｲﾝﾀｰﾏﾝ",
        is_using_center_service="0",
        consignee_center_code=""
    )
    res = b2cloud.check_shipment(session, shipment)
    assert res['success'] == False
    assert len(res['errors']) > 0


def test_regist_new_shipment(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    伝票情報の新規保存
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    shipment = b2cloud.utilities.create_dm_shipment(
        datetime.now().strftime('%Y/%m/%d'),
        "00-0000-0000",
        "テスト",
        "8900053",
        "鹿児島県",
        "鹿児島市",
        "中央町10",
        consignee_name_kana="ｲﾝﾀｰﾏﾝ",
        is_using_center_service="0",
        consignee_center_code=""
    )
    checked_feed = b2cloud.post_new_checkonly(session, [shipment])
    res = b2cloud.post_new(session, checked_feed)
    assert 'title' not in res['feed']
    assert res['feed']['entry'][0]['shipment']['consignee_name'] == "テスト"


def test_search_new_shipment(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    保存した伝票情報の検索
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.get_new(session, params={'consignee_name':'テスト'})
    assert 'title' not in res['feed']
    print(res)
    assert res['feed']['entry'][0]['shipment']['consignee_name'] == "テスト"


def test_delete_new_shipment(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    保存した伝票情報の削除
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    feed = b2cloud.get_new(session, params={'consignee_name':'テスト'})
    res = b2cloud.delete_new(session, feed)
    assert res['feed']['title'] == "Deleted."


def test_print_new_shipment_dm(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    DM伝票情報の印刷
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    shipment = b2cloud.utilities.create_dm_shipment(
        datetime.now().strftime('%Y/%m/%d'),
        "00-0000-0000",
        "テスト",
        "8900053",
        "鹿児島県",
        "鹿児島市",
        "中央町10",
        consignee_name_kana="ｲﾝﾀｰﾏﾝ",
        is_using_center_service="0",
        consignee_center_code=""
    )
    checked_feed = b2cloud.post_new_checkonly(session, [shipment])
    print(checked_feed)
    saved_feed = b2cloud.post_new(session, checked_feed)
    res = b2cloud.print_issue(session, '3', saved_feed)
    print(res[:100])
    assert res[:4].decode() == "%PDF"


def test_print_new_shipment_m5(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    m5伝票情報の印刷
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    shipment = b2cloud.utilities.create_empty_shipment()
    shipment['shipment']['service_type'] = '0'
    shipment['shipment']['shipment_date'] =  datetime.now().strftime('%Y/%m/%d')
    shipment['shipment']['invoice_code'] = '099285140601'
    shipment['shipment']['invoice_freight_no'] = '01'
    shipment['shipment']['consignee_telephone_display'] = '09034570933'
    shipment['shipment']['consignee_name'] = "テスト太郎"
    shipment['shipment']['consignee_zip_code'] = "8950012"
    shipment['shipment']['consignee_address1'] = "鹿児島県"
    shipment['shipment']['consignee_address2'] = "薩摩川内市"
    shipment['shipment']['consignee_address3'] = "平佐町３９２６−１"
    shipment['shipment']['shipper_address1'] = '鹿児島県'
    shipment['shipment']['shipper_address2'] = '鹿児島市'
    shipment['shipment']['shipper_address3'] = '中央町１０'
    shipment['shipment']['shipper_address4'] = 'キャンセビル６階'
    shipment['shipment']['shipper_name'] = 'インターマン株式会社'
    shipment['shipment']['shipper_telephone'] = '0992066878'
    shipment['shipment']['shipper_telephone_display'] = '0992066878'
    shipment['shipment']['shipper_zip_code'] = '8900053'
    shipment['shipment']['item_name1'] = '書籍'
    checked_feed = b2cloud.post_new_checkonly(session, [shipment])
    print(checked_feed)
    saved_feed = b2cloud.post_new(session, checked_feed)
    res = b2cloud.print_issue(session, 'm5', saved_feed)
    print(res[:100])
    assert res[:4].decode() == "%PDF"




def test_update_tracking(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    配送情報の更新と取得
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    # 印刷後すぐには反映されないので5回繰り返す
    for i in range(5):
        feed = b2cloud.search_history(session, consignee_name="テスト")
        if len(feed['feed']['entry']) > 0:
            break
        time.sleep(1)
    res = b2cloud.put_tracking(session, feed)
    for entry in res['feed']['entry']:
        assert entry['shipment']['consignee_name'] == "テスト"


def test_delete_history(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    発行済み伝票情報の削除
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    feed = b2cloud.search_history(session, consignee_name="テスト")
    res = b2cloud.put_history_delete(session, feed)
    for entry in res['feed']['entry']:
        assert entry['shipment']['consignee_name'] == "テスト"


def test_get_deleted(customer_code, customer_password, customer_cls_cocde, login_user_id):
    """
    削除済み伝票情報の取得
    """
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.get_history_deleted(session)
    assert res['feed']['entry'][-1]['shipment']['consignee_name'] == "テスト"


def test_get_address_info(customer_code, customer_password, customer_cls_cocde, login_user_id ,addressian_api_key):
    """
    住所情報を取得する
    """
    if addressian_api_key == "":
        print('addressian_api_keyが設定されていません。addressian_api_keyは、こちらから取得できます。 https://addressian.netlify.app/')
        assert 0
    address = "鹿児島市中央町10キャンセビル6F"
    session = b2cloud.login(customer_code, customer_password, customer_cls_cocde, login_user_id)
    res = b2cloud.utilities.get_address_info(session, addressian_api_key, address, None)
    print(res)
    assert res == {'consignee_zip_code': '8900053', 'consignee_address1': '鹿児島県', 'consignee_address2': '鹿児島市', 'consignee_address3': '中央町10', 'consignee_address4': 'キャンセビル6F'}