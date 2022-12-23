# b2cloud

ヤマト運輸株式会社の『送り状発行システムB2クラウド』を操作して伝票を印刷するためのモジュールです。
利用にあたっては、ヤマトビジネスメンバーズのaccount情報が必要となります。

## インストール

```shell
pip install b2cloud
```

## コード例

### 履歴の取得

```python
import b2cloud
import b2cloud.utilities

session = b2cloud.login('your customer_code', 'your customer_password')
dm = b2cloud.search_history(session, service_type='3')

for entry in dm['feed']['entry']:
    print(entry['shipment']['tracking_number'], entry['shipment']['consignee_name'])
```

### 新規に伝票を作成し、データに不備がないかチェックする

```python
# 伝票情報を生成する
shipment = b2cloud.utilities.create_dm_shipment(
    shipment_date='2022/12/24',
    consignee_telephone_display='00-0000-0000',
    consignee_name='テスト',
    consignee_zip_code='8900053',
    consignee_address1='鹿児島県',
    consignee_address2='鹿児島市',
    consignee_address3='中央町10',
    consignee_address4='キャンセビル６階',
    consignee_department1='インターマン株式会社'
)

# データに不備がないかチェックする
res = b2cloud.check_shipment(session, shipment)
print(res)

e.g.
{'success': True, 'errors': []}
```

### 伝票の新規保存

```python
# shipmentsをpost_new_checkonlyを通す
checked_feed = b2cloud.post_new_checkonly(session, [shipment])
# 伝票情報をB2クラウドに保存する
res = b2cloud.post_new(session, checked_feed)
```

### 保存した伝票をDM形式で印刷し各伝票毎にPDFファイルに保存する

```python
# 保存済みのDM伝票を取得
dm_feed = b2cloud.get_new(session, params={'service_type':'3'})
# DM伝票形式（１シート8枚）で印刷
dm_pdf = b2cloud.print_issue(session,'3', dm_feed)
# １伝票毎に分割する
pdfs = b2cloud.utilities.split_pdf_dm(dm_pdf)
for i in range(len(pdfs)):
    with open(f'dm_{i}.pdf', 'wb') as f:
        f.write(pdfs[i])
```

### 住所を伝票情報に変換する

住所正規化サービスAddressian([https://addressian.netlify.app/](https://addressian.netlify.app/))のAPI Keyが必要です。

```python
consignee_address = b2cloud.utilities.get_address_info(
                                                session=session,
                                                addressian_api_key='abcdefghijklmnopqrtsuvwxyz1234567890',
                                                address='鹿児島市中央町10キャンセビル6F'
                                            )
print(consignee_address)

e.g.
{
    "consignee_zip_code": "8900053",
    "consignee_address1": "鹿児島県",
    "consignee_address2": "鹿児島市",
    "consignee_address3": "中央町10",
    "consignee_address4": "キャンセビル6F"
}
```

## pytest

パラメータでログイン情報やaddressian_api_keyを指定します。

※注意

テストを実行するとテスト伝票が発行されます。
テスト実行後は、B2クラウドWEBサイトにログインして「保存分の発行」や「発行済みデータの検索」からテストデータを削除することをお勧めします。

### pytest コマンド例

```shell
pytest -q tests/test_01.py  --customer_code=0123456789 --customer_password=abcdefghi --addressian_api_key=abcdefghijklmnopqrtsuvwxyz1234567890
```

### パラメーターの一覧

```python
parser.addoption("--customer_code",      action="store", default="")
parser.addoption("--customer_password",  action="store", default="")
parser.addoption("--customer_cls_cocde", action="store", default="")
parser.addoption("--login_user_id",      action="store", default="")
parser.addoption("--addressian_api_key", action="store", default="")
```
