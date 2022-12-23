import json
import re
import time
import zlib

import lxml.html
import requests

# データキャッシュ用
CACHE = {}


def login(customer_code:str, customer_password:str, customer_cls_cocde='', login_user_id='')->requests.Session:
    '''
    ヤマトビジネスメンバーにログインして、B2クラウドに遷移したsessionを返す

    Args:
        _id:ログインID
        _pw:ログインパスワード

    Returns:
        requests.Session
    '''

    session = requests.Session()
    data = {
        'quickLoginCheckH': '',
        'BTN_NM': 'LOGIN',
        'serviceType': 'portal',
        'CSTMR_CD': customer_code,
        'CSTMR_CLS_CD': customer_cls_cocde,
        'CSTMR_PSWD': customer_password,
        'LOGIN_USER_ID': login_user_id,
        'quickLoginCheck': ''
    }
    url = 'https://bmypageapi.kuronekoyamato.co.jp/bmypageapi/login'
    for i in range(3):
        try:
            response = session.post(url, data=data)
            response.encoding = 'shift-jis'
            # ログインに成功すればユーザー情報が取得される
            html = lxml.html.fromstring(response.content)
            uels = html.xpath('//*[@id="ybmHeaderUserName"]')
            if response.status_code == 200 and len(uels) > 0:
                # B2Cloudに遷移
                session.get('https://newb2web.kuronekoyamato.co.jp/b2/d/_html/index.html?oauth&call_service_code=A')
                return session
        except:
            pass
    raise Exception('ログインに失敗しました。')


def get_history(session:requests.Session, params:dict):
    """
    発行済み伝票履歴を取得する（汎用）

    Args:
        session(requests.Session): ログイン済みのセッション
        params(dict):クエリパラメータ、件数を取得する場合は{'count':''}をパラメータに含める

    Returns:
        dict:{'feed':{'entry':['shipment':{}]}}
    """
    url = 'https://newb2web.kuronekoyamato.co.jp/b2/p/history'
    response = session.get(url, params=params)
    return json.loads(response.text)


def get_history_all(session:requests.Session):
    '''
    全ての発行済み伝票履歴を取得する。削除済みは除外される。過去90日間

    Args:
        session(requests.Session): ログイン済みのセッション

    Returns:
        dict:{'feed':{'entry':['shipment':{}]}}
    '''
    params = {'all':''}
    return get_history(session, params=params )


def get_history_deleted(session:requests.Session):
    '''
    全ての発行済み伝票履歴のうち削除済みを取得する。過去90日間

    Args:
        session(requests.Session): ログイン済みのセッション

    Returns:
        dict:{'feed':{'entry':['shipment':{}]}}
    '''
    params = {'display_flg':0}
    return get_history(session, params=params)


def put_tracking(session:requests.Session, feed:dict):
    """
    配送情報を更新する

    Args:
        session(requests.Session): ログイン済みのセッション
        feed(dict):配送状況を更新取得するshipmentを含むfeed

    Returns:
        dict:{'feed':{'entry':['shipment':{}]}}

    """
    data = __compress_feed(session, feed)
    # requestヘッダー
    headers = {
        'Content-Encoding': 'deflate',
        'Content-Type': 'application/x-msgpack; charset=x-user-defined',
        'Origin': 'https://newb2web.kuronekoyamato.co.jp',
    }
    # 配送状況を更新して取得する。配送状況の名称(tracking_status_name)はこの処理でしかとれない
    response = session.put(
        'https://newb2web.kuronekoyamato.co.jp/b2/p/history?tracking',
        headers=headers,
        data=data,
    )
    res = json.loads(response.text)
    return res


def post_new_checkonly(session:requests.Session, shipments:list):
    """
    伝票発行前チェックを行い、発行に使う情報に変換する。
    データに不備がある場合は、不備内容が格納される。

    Args:
        session(requests.Session): ログイン済みのセッション
        shipments(list):伝票情報リスト

    Returns:
        チェック結果:
            post_newの引数に使用できるよう追加変更修正がされている
            エラーがある場合は'feed'に'title':'Error'が格納され、該当entryにerror[詳細]が格納される
    """
    # POST用の入れ物
    json_data = {'feed': {'entry': shipments}}

    # postに必須
    headers = {'Origin': 'https://newb2web.kuronekoyamato.co.jp'}

    # 内容の事前チェック
    res = session.post('https://newb2web.kuronekoyamato.co.jp/b2/p/new?checkonly', headers=headers, json=json_data)
    return json.loads(res.text)


def check_shipment(session:requests.Session, shipment):
    """
    伝票情報に不備がないか単体でチェックを行う。
    post_new_checkonlyの戻り値を扱いやすいように変更したもの

    Args:
        session(requests.Session): ログイン済みのセッション
        shipment(dict):伝票情報

    Returns:
        dict:チェック結果
    """
    res = post_new_checkonly(session, shipments=[shipment])
    errors = res['feed']['entry'][0].get('error',[])
    return {'success':len(errors)==0, 'errors': errors}


def check_shipments(session:requests.Session, shipments:list):
    """
    伝票情報に不備がないかチェックを行う。
    post_new_checkonlyの戻り値を扱いやすいように変更したもの

    Args:
        session(requests.Session): ログイン済みのセッション
        shipments(list[dict]):伝票情報のリスト

    Returns:
        list[dict:チェック結果]
    """
    res = post_new_checkonly(session, shipments=shipments)
    ret = []
    for entry in res['feed']['entry']:
        errors = entry.get('error',[])
        ret.append({'success':len(errors)==0, 'errors': errors})
    return ret


def post_new(session:requests.Session, checked_feed:dict):
    """
    伝票を登録する。
    引数checked_feedは、post_new_checkonlyの戻り値

    Args:
        session(requests.Session): ログイン済みのセッション
        checked_feed(dict): post_new_checkonlyの結果

    Return:
        dict'{'feed':{'entry':[shipment]}}
            entryには'id'が付加されていないので注意
    """
    # shipment_flgに'0'を入れる
    for i in range(len(checked_feed['feed']['entry'])):
        checked_feed['feed']['entry'][i]['shipment']['shipment_flg'] = '0'

    # request headers
    headers = {'Origin': 'https://newb2web.kuronekoyamato.co.jp'}
    # 登録
    res = session.post('https://newb2web.kuronekoyamato.co.jp/b2/p/new', headers=headers, json=checked_feed)
    return json.loads(res.text)


def get_new(session:requests.Session, params=None):
    """
    登録されている発行前伝票情報を取得する

    Args:
        session(requests.Session): ログイン済みのセッション
        params(dict): 検索パラメータ。get_historyと同じパラメータが使える。countを指定すると件数

    Return:
        dict'{'feed':{'entry':[shipment]}}
            entryには'id'が付加されている
    """
    headers =  {'Origin': 'https://newb2web.kuronekoyamato.co.jp'}
    url = 'https://newb2web.kuronekoyamato.co.jp/b2/p/new'

    res = session.get(url, headers=headers, params=params)
    return json.loads(res.text)


def delete_new(session:requests.Session, feed:dict):
    """
    保存済みデータを削除する

    Args:
        session:ログイン済みのセッション
        feed:shipmentを含むfeed

    Returns:
        feed(dict)
    """
    # tracking更新処理5 圧縮データを前2バイト、後ろ4バイトをトリムする
    data = __compress_feed(session, feed)
    # requestヘッダー
    headers = {
        'Content-Encoding': 'deflate',
        'Content-Type': 'application/x-msgpack; charset=x-user-defined',
        'Origin': 'https://newb2web.kuronekoyamato.co.jp',
    }
    # 配送状況を更新して取得する。配送状況の名称(tracking_status_name)はこの処理でしかとれない
    response = session.delete(
        'https://newb2web.kuronekoyamato.co.jp/b2/p/new',
        headers=headers,
        data=data,
    )
    res = json.loads(response.text)
    return res


def print_issue(session:requests.Session, print_type:str, entry_feed:dict):
    """
    伝票情報のPDFを取得する。新規、再印刷共通
    新規の伝票はこの処理によってtracking_numberが振られて印刷済みになる（IDは更新される）

    Args:
        session(requests.Session): ログイン済みのセッション
        print_type: 'm':A4マルチ, 'm5':A5マルチ, '3':dm , '7':ネコポス

    Returns:
        bytearry: 伝票のPDFデータ
    """
    # tracking_numberの有無で新規か、再印刷か判断する。
    if 'tracking_number' in entry_feed['feed']['entry'][0]['shipment']:
        isnew = True
    else:
        isnew = False

    # entry_feedを印刷用データに変換する
    entries = []
    for entry in entry_feed['feed']['entry']:
        if 'id ' in entry:
            _id = entry['id']
        else:
            try:
                _id = entry['link'][0]['___href'] + "," + entry['shipment']['upd_revision']
            except:
                _id = entry['link'][0]['___href'] + ",1"

        entries.append(
            {
                'id':_id,
                'shipment':{
                    'shipment_flg': '1',
                    'printer_type':     entry['shipment']['printer_type'],
                    'service_type':     entry['shipment']['service_type'],
                    'is_cool':          entry['shipment']['is_cool'],
                    'tracking_number':  entry['shipment']['tracking_number'],
                    'package_qty':      entry['shipment']['package_qty'],
                    'is_agent':         entry['shipment']['is_agent'],
                    'created_ms':       entry['shipment']['created_ms'],
                }
            }
        )
    json_data = {
            'feed': {
                'entry': entries
            }
        }
    # PDFデータの作成開始
    headers = {'Origin': 'https://newb2web.kuronekoyamato.co.jp'}

    # tracking_numberの有無で新規か、再印刷か判断する。
    if entry_feed['feed']['entry'][0]['shipment']['tracking_number'].startswith('OMN'):
        # 新規印刷
        response = session.post(f'https://newb2web.kuronekoyamato.co.jp/b2/p/new?issue&print_type={print_type}&sort1=service_type&sort2=created&sort3=created', headers=headers, json=json_data)
    else:
        # 再印刷
        response = session.put(f'https://newb2web.kuronekoyamato.co.jp/b2/p/history?reissue&print_type={print_type}&sort1=service_type&sort2=created&sort3=created',headers=headers, json=json_data)

    issue_no = json.loads(response.text)['feed']['title']
    # _res['feed']['title'] == "Success"になるまでループする
    for i in range(100):
        res = session.get(f'https://newb2web.kuronekoyamato.co.jp/b2/p/polling?issue_no={issue_no}&service_no=interman')
        _res = json.loads(res.text)
        if _res['feed']['title'] == "Success":
            break
        time.sleep(0.1)
    else:
        raise Exception("PDFデータ生成に失敗")
    # 完了後にcheckを読み込むレスポンスは空
    _ = session.get(f'https://newb2web.kuronekoyamato.co.jp/b2/p/B2_OKURIJYO?checkonly=1&issue_no={issue_no}')

    # 生成されたPDFデータをダウンロードする
    res = session.get(f'https://newb2web.kuronekoyamato.co.jp/b2/p/B2_OKURIJYO?issue_no={issue_no}&fileonly=1')

    return res.content


def put_history_delete(session:requests.Session, feed:dict)->dict:
    """
    feedに含まれるshipmentを削除(display=0)にする

    Args:
        session:ログイン済みのセッション
        feed:shipmentを含むfeed

    Returns:
        feed(dict)
    """
    entries = []
    for entry in feed['feed']['entry']:
        _entry = {
            'id':entry['id'],
            'link':entry['link'],
            'shipment':{'tracking_number':entry['shipment']['tracking_number']}
        }
        entries.append(_entry)
    _feed = {'feed':{'entry':entries}}
    url = 'https://newb2web.kuronekoyamato.co.jp/b2/p/history?display_flg=0'
    headers = {
    'Origin': 'https://newb2web.kuronekoyamato.co.jp',
    }
    response = session.put(url, headers=headers, json=_feed)
    return json.loads(response.text)


def put_history_display(session:requests.Session, feed:dict):
    """
    削除に移す
    """
    entries = []
    for entry in feed['feed']['entry']:
        _entry = {
            'id':entry['id'],
            'link':entry['link'],
            'shipment':{'tracking_number':entry['shipment']['tracking_number']}
        }
        entries.append(_entry)
    _feed = {'feed':{'entry':entries}}
    url = 'https://newb2web.kuronekoyamato.co.jp/b2/p/history?display_flg=1'
    headers = {
    'Origin': 'https://newb2web.kuronekoyamato.co.jp',
    }
    response = session.put(url, headers=headers, json=_feed)
    return json.loads(response.text)


def get_dm_number_print(session:requests.Session, params:dict):
    """
    DM便番号一覧のPDFを取得する
    """
    _params = {}
    _params['dmnumberlist'] = ''
    _params['print_type'] = 'D2'
    _params.update(params)
    response = session.get('https://newb2web.kuronekoyamato.co.jp/b2/p/history', params=_params)

    issue_no = json.loads(response.text)['feed']['title']
    # _res['feed']['title'] == "Success"になるまでループする
    for i in range(100):
        res = session.get(f'https://newb2web.kuronekoyamato.co.jp/b2/p/polling?issue_no={issue_no}&service_no=interman')
        _res = json.loads(res.text)
        if _res['feed']['title'] == "Success":
            break
        time.sleep(0.1)
    else:
        raise Exception("PDFデータ生成に失敗")
    # 完了後にcheckを読み込むレスポンスは空
    res = session.get(f'https://newb2web.kuronekoyamato.co.jp/b2/p/B2_OKURIJYO?checkonly=1&issue_no={issue_no}')

    # 生成されたPDFデータをダウンロードする
    res = session.get(f'https://newb2web.kuronekoyamato.co.jp/b2/p/B2_OKURIJYO?issue_no={issue_no}&fileonly=1')

    return res.content


def search_history(session:requests.Session,
        service_type=None,
        consignee_name= None,
        shipment_plan_from= None,
        shipment_plan_to= None,
        tracking_number= None,
        display_flg= "1",
        shipment_number= None,
        invoice_name= None,
        invoice_code= None,
        consignee_telephone= None,
        consignee_name_kana= None,
        consignee_department1= None,
        consignee_department2= None,
        shipper_name= None,
        shipper_name_kana= None,
        item_name1= None,
        item_name2= None,
        shipment_result_date_from= None,
        shipment_result_date_to= None,
        creator_loginid= None,
        issuer_loginid= None,
        updater_loginid= None,
        dangerous_flg= None,
        issued_date= None,
        closure_key= None,
        search_title1= None,
        search_key1= None,
        search_title2= None,
        search_key2= None,
        search_title3= None,
        search_key3= None,
        search_title4= None,
        search_key4= None,
        search_title5= None,
        search_key5 = None,
        tracking_number_from=None,
        tracking_number_to=None
    ):
    """
    発行済み伝票情報の検索
    """
    args = locals().copy()
    params = {}
    params['all']=''
    for k, v in args.items():
        if k == 'session':
            continue
        elif k == "shipment_plan_from" and v is not None:
            params[f'shipment_date-ge-{v.strftime("%Y%m%d")}'] = ''
        elif k == "shipment_plan_to" and v is not None:
            params[f'shipment_date-le-{v.strftime("%Y%m%d")}'] = ''
        elif k == "shipment_result_date_from" and v is not None:
            params[f'shipment_result_date-ge-{v.strftime("%Y%m%d")}'] = ''
        elif k == "shipment_result_date_to" and v is not None:
            params[f'shipment_result_date-le-{v.strftime("%Y%m%d")}'] = ''
        elif k == "tracking_number_from" and v is not None:
            params[f'tracking_number-ge-{v}'] = ''
        elif k == "tracking_number_to" and v is not None:
            params[f'tracking_number-le-{v}'] = ''
        elif v is not None:
            params[k] = v
    return get_history(session, params=params)


def __compress_feed(session, feed):
    """
    feedを圧縮する
    """
    def __create_template():
        """
        配送状況更新用のtemplateを生成する(javascriptの解析して実装)
        """
        # キャッシュがある場合は、キャッシュを返す
        if 'template' in CACHE:
            return CACHE['template']

        def list2dict(fields):
            for x in fields:
                if x[0] == " ":
                    break
            else:
                return fields

            ret = {}
            fname = None
            for _field in fields:
                field = re.match(r'\s*[0-9a-zA-Z_]+', _field).group()
                if field[0] != " ":
                    if fname is not None:
                        ret[fname] = list2dict(_fields)
                    _fields = {}
                    fname =field
                else:
                    _fields[field[1:].replace('{}','')] = ""
            ret[fname] = list2dict(_fields)
            return ret

        response = session.get('https://newb2web.kuronekoyamato.co.jp/b2/d/_settings/template')
        fields = ["author{}", " name", " uri", " email", "category{}", " ___term",
                " ___scheme", " ___label", "content", " ___src", " ___type", " ______text",
                "contributor{}", " name", " uri", " email", "id", "link{}", " ___href",
                " ___rel", " ___type", " ___title", " ___length", "published", "rights",
                "rights____type", "summary", "summary____type", "title", "title____type",
                "subtitle", "subtitle____type", "updated"
            ]
        fields.extend(response.text.split('\n'))
        ret = list2dict(fields)
        CACHE['template'] = ret
        return ret


    def __create_fieled_list(template, feed):
        """
        dict -> listする(javascriptの解析して実装)
        """
        def extend(_temp, item):
            if type(item) is str:
                return item

            if type(item) is dict:
                ret = []
                for temp in _temp:
                    if temp in item:
                        ret.append(extend(_temp[temp], item[temp]))
                    else:
                        ret.append(None)
                return ret
            if type(item) is list:
                ret = []
                islink=True
                for _item in item:
                    res = extend(_temp, _item)
                    ret.append(res)
                return ret
            raise
        ret = [None]*15
        ret[14] = extend(template, feed['feed']['entry'])
        return ret


    def __b2_encode(field_list):
        """
        配列にしたデータをバイト列にする(javascriptを解析して実装）
        """
        if field_list is None:
            return [192]
        if type(field_list) == dict:
            raise Exception("未実装1")
        if type(field_list) is list:
            ret = []
            t = len(field_list)
            n = 144 + t if t < 16 else 220
            ret.append(n)
            if n == 220:
                for x in t.to_bytes(2, 'big'):
                    ret.append(x)
            for _item in field_list:
                ret.extend(__b2_encode(_item))
            return ret
        if type(field_list) is str:
            bitem = field_list.encode('utf-8')
            t = len(bitem)
            o = 1 if t < 32 else 2 if t < 255 else 3 if t<65535 else 5
            u = 160 + t if o==1 else 215 + o if o<=3 else 219
            ret = []
            if o == 1:
                ret.append(u)
            elif o > 1:
                ret.append(u)
                flg = False
                for x in t.to_bytes(6,'big'):
                    if x > 0:
                        flg = True
                    if flg:
                        ret.append(t)
            elif o == 3:
                ret.append(u)
                ret.append(t>>8)
                ret.append(t)
            for c in bitem:
                ret.append(c)
            return ret
        raise Exception("未実装2")

    template = __create_template()
    # tracking更新処理2 feedをfield_listに変換する
    field_list = __create_fieled_list(template, feed)
    # tracking更新処理3 field_listを独自encodeする
    encoded = __b2_encode(field_list)
    # tracking更新処理4 zip圧縮する
    compressed = zlib.compress(bytes(encoded))
    # tracking更新処理5 圧縮データを前2バイト、後ろ4バイトをトリムする
    ret = compressed[2:-4]
    return ret
