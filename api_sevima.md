Example request:
import requests
import json

url = 'https://api.sevimaplatform.com/siakadcloud/v1/user/login'
payload = {
    "email": "staging-siacloud-dd@yopmail.com",
    "password": "12345678"
}
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'X-App-Key': '{APP_KEY}',
  'X-Secret-Key': '{SECRET_KEY}'
}

response = requests.request('POST', url, headers=headers, json=payload)
response.json()
Example response (200):


{
    "type": "user",
    "url": "https://api.sevimaplatform.com/siakadcloud/v1/user/login",
    "id": "1",
    "attributes": {
        "user_id": "1",
        "nama": "Contoh Nama",
        "email": "contoh@sevima.com",
        "status_aktif": "1",
        "role": [
            {
                "id_role": "DSN",
                "id_pegawai": "1",
                "nip": "1234567890",
                "nama_role": "Dosen",
                "id_satker": "55201",
                "nama_satker": "Contoh Program Studi"
            }
        ]
    }
}

 
Example response (401, Akun Tidak Memiliki Akses):

